from importlib.metadata import version

import duckdb
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
from splink.comparison_library import CosineSimilarityAtThresholds, ExactMatch


def main() -> None:
    print(f"splink={version('splink')}")
    print(f"duckdb={duckdb.__version__}")
    print(
        "api="
        + ",".join(
            [
                Linker.__name__,
                SettingsCreator.__name__,
                DuckDBAPI.__name__,
                ExactMatch.__name__,
                CosineSimilarityAtThresholds.__name__,
            ]
        )
    )
    print(f"blocking={block_on('clinic_slug')}")


if __name__ == "__main__":
    main()
