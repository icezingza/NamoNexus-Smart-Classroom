from uvicorn import run

from namo_core.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    run(
        "namo_core.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    main()
