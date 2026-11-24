#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Monitoramento de Integridade do Sistema (SMS)
Módulo Backend e CLI integrado ao Projeto Meridian
"""

import hashlib
import json
import logging
import threading
import time
import signal
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass


# ============================================
# Configuração de Logging e Auditoria
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrity_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================
# Definições de Classes Principais
# ============================================

@dataclass
class FileHash:
    """Classe para armazenar hash de arquivo"""
    filepath: str
    current_hash: str
    expected_hash: Optional[str] = None
    last_modified: float = 0.0
    file_size: int = 0
    status: str = "OK"


@dataclass
class IntegrityReport:
    """Classe para relatórios de integridade"""
    total_files: int
    modified_files: int
    new_files: int
    deleted_files: int
    critical_alerts: List[str]
    timestamp: datetime


# ============================================
# Sistema Principal de Monitoramento
# ============================================

class IntegrityMonitor:
    """Classe principal para monitoramento de integridade"""

    def __init__(self, critical_paths: Optional[List[str]] = None, check_interval: int = 300):
        self.critical_paths: List[Path] = [Path(p).resolve() for p in (critical_paths or [])]
        self.check_interval = check_interval
        self.hash_database: Dict[str, Dict[str, str]] = {}
        self.modified_files: List[FileHash] = []
        self.alert_messages: List[str] = []
        self.last_check_time: Optional[str] = None

        # Controle de Thread para CLI e Interface Gráfica
        self.stop_event = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None
        self.is_running: bool = False

        # Configuração de diretório para monitoramento
        self.monitor_dir = Path(__file__).parent.resolve()
        self.db_file = self.monitor_dir / "integrity_hashes.json"
        self.report_dir = self.monitor_dir / "reports"
        self.report_dir.mkdir(exist_ok=True)

        # Carrega banco existente automaticamente se disponível
        if self.db_file.exists():
            self.import_database(self.db_file)

        # Adiciona novos caminhos passados na inicialização
        for p in self.critical_paths:
            if str(p) not in self.hash_database and p.exists():
                self.add_path(str(p))

        logger.info(f"Sistema iniciado em: {self.monitor_dir}")

    def hash_file(self, filepath: Path) -> Optional[Dict[str, str]]:
        """Calcula hash SHA256 e MD5 de um arquivo"""
        sha256 = hashlib.sha256()
        md5 = hashlib.md5()

        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
                    md5.update(chunk)

            return {
                'sha256': sha256.hexdigest(),
                'md5': md5.hexdigest()
            }
        except Exception as e:
            logger.error(f"Erro ao calcular hash de {filepath}: {e}")
            return None

    def initialize_monitoring(self) -> bool:
        """Inicializa o monitoramento criando hashes iniciais"""
        try:
            logger.info("Iniciando cálculo de hashes iniciais...")

            for path in self.critical_paths:
                if path.exists() and path.is_file():
                    hashes = self.hash_file(path)
                    if hashes:
                        self.hash_database[str(path)] = {
                            'sha256': hashes['sha256'],
                            'md5': hashes['md5']
                        }

            self.save_hash_database()
            logger.info(f"Banco de hashes inicializado com {len(self.hash_database)} arquivos")
            return True
        except Exception as e:
            logger.error(f"Falha ao inicializar monitoramento: {e}")
            return False

    def save_hash_database(self) -> bool:
        """Salva o banco de dados de hashes"""
        return self.export_database(self.db_file)

    def check_file_integrity(self, filepath: Path) -> FileHash:
        """Verifica integridade de um arquivo individual"""
        path_str = str(filepath.resolve()) if filepath.exists() else str(filepath)
        expected_hash = self.hash_database.get(path_str)

        try:
            if not filepath.exists():
                return FileHash(
                    filepath=path_str,
                    current_hash="",
                    expected_hash=expected_hash.get('sha256') if expected_hash else None,
                    status="DELETED"
                )

            current_hashes = self.hash_file(filepath)
            if not current_hashes:
                return FileHash(filepath=path_str, current_hash="", status="ERROR")

            if expected_hash:
                sha256_match = current_hashes['sha256'] == expected_hash.get('sha256')
                md5_match = current_hashes['md5'] == expected_hash.get('md5')
                status = "OK" if (sha256_match and md5_match) else "MODIFIED"
            else:
                status = "NEW"

            stat = filepath.stat()
            return FileHash(
                filepath=path_str,
                current_hash=current_hashes.get('sha256', ''),
                expected_hash=expected_hash.get('sha256') if expected_hash else None,
                last_modified=stat.st_mtime,
                file_size=stat.st_size,
                status=status
            )
        except Exception as e:
            logger.error(f"Erro ao verificar arquivo {filepath}: {e}")
            return FileHash(filepath=path_str, current_hash="", status="ERROR")

    def scan_directory(self) -> List[FileHash]:
        """Varre caminhos monitorados e retorna resultados"""
        self.modified_files.clear()
        self.alert_messages.clear()

        # Garante sincronia entre hash_database e critical_paths
        monitored_paths = [Path(p) for p in self.hash_database.keys()]
        for p in self.critical_paths:
            if p not in monitored_paths:
                monitored_paths.append(p)

        for path in monitored_paths:
            result = self.check_file_integrity(path)
            self.modified_files.append(result)

            if result.status == "MODIFIED":
                self.alert_messages.append(
                    f"ALERTA: Arquivo modificado não autorizado! Caminho: {result.filepath}"
                )
            elif result.status == "NEW":
                self.alert_messages.append(
                    f"INFORMAÇÃO: Novo arquivo detectado! Caminho: {result.filepath}"
                )
            elif result.status == "DELETED":
                self.alert_messages.append(
                    f"ALERTA CRÍTICO: Arquivo deletado! Caminho: {result.filepath}"
                )

        self.last_check_time = datetime.now().isoformat()
        return self.modified_files

    def monitor_realtime(self):
        """Loop de monitoramento em tempo real"""
        logger.info(f"Iniciando monitoramento em tempo real a cada {self.check_interval}s")
        self.is_running = True
        self.stop_event.clear()

        while not self.stop_event.is_set():
            self.scan_directory()
            if any(f.status != "OK" for f in self.modified_files):
                self.generate_report()
            self.stop_event.wait(self.check_interval)

        self.is_running = False
        logger.info("Monitoramento em tempo real finalizado.")

    def start_background_monitoring(self) -> bool:
        """Inicia a thread em segundo plano de forma segura para interfaces web"""
        if self.is_running:
            return False
        self.monitor_thread = threading.Thread(target=self.monitor_realtime, daemon=True)
        self.monitor_thread.start()
        return True

    def stop_background_monitoring(self):
        """Sinaliza parada graciosa da thread"""
        self.stop_event.set()
        self.is_running = False

    def generate_report(self) -> Optional[Path]:
        """Gera relatório de integridade em JSON"""
        try:
            modified_count = sum(1 for f in self.modified_files if f.status == "MODIFIED")
            report = IntegrityReport(
                total_files=len(self.hash_database),
                modified_files=modified_count,
                new_files=sum(1 for f in self.modified_files if f.status == "NEW"),
                deleted_files=sum(1 for f in self.modified_files if f.status == "DELETED"),
                critical_alerts=list(self.alert_messages),
                timestamp=datetime.now()
            )

            report_file = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'total_files': report.total_files,
                    'modified_files': report.modified_files,
                    'new_files': report.new_files,
                    'deleted_files': report.deleted_files,
                    'alerts': report.critical_alerts,
                    'timestamp': report.timestamp.isoformat()
                }, f, indent=2, ensure_ascii=False)

            logger.info(f"Relatório gerado em: {report_file}")
            return report_file
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")
            return None

    def run_once(self) -> bool:
        """Executa verificação única"""
        if not self.hash_database:
            if not self.initialize_monitoring():
                return False

        results = self.scan_directory()
        if results:
            self.generate_report()
        return True

    def get_status_summary(self) -> Dict:
        """Retorna resumo do status atual"""
        return {
            'critical_paths': len(self.critical_paths),
            'files_monitored': len(self.hash_database),
            'last_check': self.last_check_time or datetime.now().isoformat(),
            'is_running': self.is_running,
            'ok_count': sum(1 for f in self.modified_files if f.status == "OK"),
            'modified_count': sum(1 for f in self.modified_files if f.status == "MODIFIED"),
            'new_count': sum(1 for f in self.modified_files if f.status == "NEW"),
            'deleted_count': sum(1 for f in self.modified_files if f.status == "DELETED")
        }

    def export_database(self, output_path: Optional[Path] = None) -> bool:
        """Exporta o banco de dados de hashes para arquivo"""
        target_path = Path(output_path) if output_path else self.db_file
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'hashes': self.hash_database
            }
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Banco de dados salvo em: {target_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao exportar banco de dados: {e}")
            return False

    def import_database(self, input_path: Path) -> bool:
        """Importa banco de dados de hashes de arquivo"""
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.hash_database = data.get('hashes', {})
            self.critical_paths = [Path(p) for p in self.hash_database.keys()]
            logger.info(f"Banco de dados importado com {len(self.hash_database)} arquivos")
            return True
        except Exception as e:
            logger.error(f"Erro ao importar banco de dados: {e}")
            return False

    def reset_monitoring(self) -> bool:
        """Reseta o monitoramento (limpa hashes e alertas)"""
        self.hash_database.clear()
        self.critical_paths.clear()
        self.modified_files.clear()
        self.alert_messages.clear()
        self.save_hash_database()
        logger.info("Monitoramento resetado com sucesso")
        return True

    def add_path(self, path: str) -> bool:
        """Adiciona novo caminho para monitoramento"""
        new_path = Path(path).resolve()
        if not new_path.exists() or not new_path.is_file():
            logger.warning(f"Arquivo inválido ou inexistente: {new_path}")
            return False

        path_str = str(new_path)
        hashes = self.hash_file(new_path)
        if hashes:
            self.hash_database[path_str] = hashes
            if new_path not in self.critical_paths:
                self.critical_paths.append(new_path)
            self.save_hash_database()
            logger.info(f"Novo caminho adicionado: {path_str}")
            return True
        return False

    def remove_path(self, path: str) -> bool:
        """Remove caminho do monitoramento"""
        path_resolved = str(Path(path).resolve())
        target_key = path_resolved if path_resolved in self.hash_database else path

        if target_key in self.hash_database:
            del self.hash_database[target_key]
            self.critical_paths = [p for p in self.critical_paths if str(p) != target_key]
            self.save_hash_database()
            logger.info(f"Caminho removido: {target_key}")
            return True
        return False

    def get_detailed_report(self, filepath: Optional[str] = None) -> Dict:
        """Gera relatório detalhado de um arquivo específico ou geral"""
        if filepath:
            path_obj = Path(filepath).resolve()
            key = str(path_obj) if str(path_obj) in self.hash_database else filepath

            if key in self.hash_database:
                db_hash = self.hash_database[key]
                exists = path_obj.exists()
                current_hashes = self.hash_file(path_obj) if exists else None

                if not exists:
                    status = "DELETED"
                elif current_hashes and (
                    current_hashes['sha256'] != db_hash.get('sha256') or
                    current_hashes['md5'] != db_hash.get('md5')
                ):
                    status = "MODIFIED"
                else:
                    status = "OK"

                return {
                    'filepath': key,
                    'expected_sha256': db_hash.get('sha256'),
                    'current_sha256': current_hashes['sha256'] if current_hashes else None,
                    'expected_md5': db_hash.get('md5'),
                    'current_md5': current_hashes['md5'] if current_hashes else None,
                    'status': status,
                    'size': path_obj.stat().st_size if exists else 0,
                    'modified_time': datetime.fromtimestamp(path_obj.stat().st_mtime).isoformat() if exists else None
                }
            return {'error': f'Arquivo não encontrado no banco: {filepath}'}

        return self.get_status_summary()


# ============================================
# Interface de Linha de Comando (Isolada)
# ============================================

def parse_arguments():
    parser = argparse.ArgumentParser(description='Sistema de Monitoramento de Integridade (SMS)')
    parser.add_argument('--init', nargs='+', help='Inicializa monitoramento com arquivos especificados')
    parser.add_argument('--scan', action='store_true', help='Executa varredura única de integridade')
    parser.add_argument('--monitor', action='store_true', help='Inicia monitoramento em tempo real')
    parser.add_argument('--status', action='store_true', help='Mostra status atual do sistema')
    parser.add_argument('--export', type=str, help='Exporta banco de dados para arquivo JSON')
    parser.add_argument('--import', dest='import_', type=str, help='Importa banco de dados de arquivo JSON')
    parser.add_argument('--reset', action='store_true', help='Reseta o monitoramento (limpa hashes)')
    parser.add_argument('--add', type=str, help='Adiciona novo caminho para monitoramento')
    parser.add_argument('--remove', type=str, help='Remove caminho do monitoramento')
    parser.add_argument('--file', type=str, help='Verifica arquivo específico')
    return parser.parse_args()


def main():
    args = parse_arguments()
    monitor = IntegrityMonitor(critical_paths=args.init if args.init else [], check_interval=300)

    if args.init:
        monitor.initialize_monitoring()
    elif args.reset:
        monitor.reset_monitoring()
    elif args.import_:
        monitor.import_database(Path(args.import_))
    elif args.export:
        monitor.export_database(Path(args.export))
    elif args.scan:
        monitor.run_once()
    elif args.status:
        monitor.scan_directory()
        print(json.dumps(monitor.get_status_summary(), indent=2, ensure_ascii=False))
    elif args.monitor:
        def signal_handler(sig, frame):
            print("\nEncerrando monitoramento graciosamente...")
            monitor.stop_background_monitoring()

        signal.signal(signal.SIGINT, signal_handler)
        monitor.start_background_monitoring()
        print("Monitoramento iniciado. Pressione Ctrl+C para parar.")
        while monitor.is_running:
            time.sleep(1)
    elif args.add:
        monitor.add_path(args.add)
    elif args.remove:
        monitor.remove_path(args.remove)
    elif args.file:
        print(json.dumps(monitor.get_detailed_report(args.file), indent=2, ensure_ascii=False))
    else:
        monitor.run_once()


if __name__ == "__main__":
    main()