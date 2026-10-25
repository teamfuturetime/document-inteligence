import argparse
from pathlib import Path

from document_pipeline.config import PipelineConfig
from document_pipeline.errors import PipelineError
from document_pipeline.service import DocumentPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-02 real inference; never reads annotations.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--document-type", choices=("hoa_don", "don_de_nghi"), required=True)
    parser.add_argument("--tessdata-dir", type=Path, required=True)
    parser.add_argument("--executable", default="tesseract")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Output phải khác input")
        config = (
            PipelineConfig.model_validate_json(args.config.read_text(encoding="utf-8"))
            if args.config
            else PipelineConfig()
        )
        with args.input.open("rb") as stream:
            data = stream.read(config.max_upload_bytes + 1)
        result = DocumentPipeline(args.tessdata_dir, args.executable, config).run(
            data, args.document_type
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive create prevents accidentally replacing an earlier run's evidence.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(result.model_dump_json(indent=2) + "\n")
    except (PipelineError, OSError, ValueError) as exc:
        parser.exit(1, f"{getattr(exc, 'code', 'INVALID_INPUT')}: {exc}\n")


if __name__ == "__main__":
    main()
