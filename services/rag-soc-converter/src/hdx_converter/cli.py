import argparse
from pathlib import Path
import sys
import logging
import uvicorn

# Импорты из пакета (после установки через pip install -e .)
from hdx_converter.models.config import ConverterConfig
from hdx_converter.core.converter import HDXConverter
from hdx_converter.api import create_app

# Импорт версии из __init__.py
try:
    from hdx_converter import __version__, __author__, __year__
except ImportError:
    __version__ = "1.5.1"
    __author__ = "HDX Converter Team"
    __year__ = "03.2026"


def main():
    parser = argparse.ArgumentParser(
        description='Convert HDX documentation to multiple formats with metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  hdx-converter input.hdx
  hdx-converter input.hdx -o output_dir --max-articles 100
  hdx-converter input.hdx --skip-extract --no-md
        """
    )

    # Основные аргументы
    parser.add_argument('hdx_file', type=Path,
                       help='Path to HDX file')
    parser.add_argument('-o', '--output', type=Path, default=Path('hdx_output'),
                       help='Output directory (default: hdx_output)')

    # Настройки обработки
    parser.add_argument('-n', '--max-articles', type=int,
                       help='Process only first N articles')
    parser.add_argument('--skip-extract', action='store_true',
                       help='Skip HDX extraction and use existing HTML backup files')

    # Настройки форматов вывода
    parser.add_argument('--no-md', action='store_true',
                       help='Skip Markdown generation')
    parser.add_argument('--no-txt', action='store_true',
                       help='Skip text file generation')
    parser.add_argument('--no-json', action='store_true',
                       help='Skip JSON metadata generation')
    parser.add_argument('--no-images', action='store_true',
                       help='Skip image copying')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip HTML backup')

    # Настройки логирования
    log_group = parser.add_mutually_exclusive_group()
    log_group.add_argument('-v0', '--silent', action='store_true',
                       help='Silent mode - only errors to log, nothing to console')
    log_group.add_argument('-v1', '--short', action='store_true',
                       help='Short mode - warnings and above to log, errors to console')
    log_group.add_argument('-v2', '--normal', action='store_true',
                       help='Normal mode (default) - info and above to log, errors to console')
    log_group.add_argument('-v3', '--debug', action='store_true',
                       help='Debug mode - debug and above to log, errors to console')

    # Настройки валидации
    parser.add_argument('--no-validate', action='store_true',
                       help='Skip metadata validation')
    parser.add_argument('--no-stats', action='store_true',
                       help='Skip statistics collection and display')

    args = parser.parse_args()

    # Определение verbose_level
    verbose_level = 2  # по умолчанию normal
    if args.silent:
        verbose_level = 0
    elif args.short:
        verbose_level = 1
    elif args.normal:
        verbose_level = 2
    elif args.debug:
        verbose_level = 3

    # Проверка входного файла
    if not args.hdx_file.exists() and not args.skip_extract:
        print(f"Error: HDX file '{args.hdx_file}' not found")
        sys.exit(1)

    # Проверка наличия tqdm для прогресс-бара
    try:
        import tqdm
        HAS_TQDM = True
    except ImportError:
        HAS_TQDM = False
        print("Note: tqdm not installed. Progress bars will be disabled.")
        print("Install with: pip install tqdm")

    # Создание конфигурации
    config = ConverterConfig(
        output_dir=args.output,
        max_articles=args.max_articles,
        skip_extract=args.skip_extract,
        generate_markdown=not args.no_md,
        generate_text=not args.no_txt,
        generate_json_metadata=not args.no_json,
        copy_images=not args.no_images,
        backup_html=not args.no_backup,
        validate_metadata=not args.no_validate,
        collect_statistics=not args.no_stats,
        print_statistics=not args.no_stats,
        log_level="DEBUG"
    )

    # Вывод версии в консоль
    version_msg = f"HDX Converter v.{__version__} {__year__} - {__author__}"
    print(version_msg)

    # Создание и запуск конвертера
    try:
        from hdx_converter.utils.logger import HDXLogger
        logger = HDXLogger(config, verbose_level).get_logger()
        logger.info(version_msg)

        converter = HDXConverter(config, logger)
        converter.convert(args.hdx_file)

        # Проверка наличия ошибок для кода возврата
        if hasattr(converter, 'stats_collector') and converter.stats_collector.has_errors():
            logger.error(f"Conversion completed with errors: {converter.stats_collector.conversion_stats.errors_encountered} errors")
            sys.exit(1)
        else:
            sys.exit(0)

    except KeyboardInterrupt:
        print("\nConversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


def run_api():
    """Run API server."""
    # Парсим аргументы для API режима
    api_parser = argparse.ArgumentParser(description='Run Converter API server')
    api_parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    api_parser.add_argument('--port', type=int, default=8080, help='Port to bind')
    api_parser.add_argument('--log-level', type=int, default=2,
                           choices=[0, 1, 2, 3],
                           help='Log level: 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG')
    api_parser.add_argument('--kafka-bootstrap-servers',
                           help='Kafka bootstrap servers (optional)')
    api_parser.add_argument('--kafka-enabled', action='store_true',
                           help='Enable Kafka notifications')

    args = api_parser.parse_args()

    # Настройка логгера для API
    log_level = logging.INFO
    if args.log_level >= 3:
        log_level = logging.DEBUG
    elif args.log_level >= 2:
        log_level = logging.INFO
    elif args.log_level >= 1:
        log_level = logging.WARNING
    else:
        log_level = logging.ERROR

    logging.basicConfig(level=log_level)
    logger = logging.getLogger("converter")

    # Создание FastAPI приложения
    app = create_app(
        logger=logger,
        kafka_bootstrap_servers=args.kafka_bootstrap_servers,
        kafka_enabled=args.kafka_enabled
    )

    # Запуск сервера
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info"
    )


if __name__ == "__main__":
    # Проверяем, вызван ли скрипт в режиме API
    if len(sys.argv) > 1 and sys.argv[1] == "api":
        sys.argv.pop(1)
        run_api()
    else:
        main()