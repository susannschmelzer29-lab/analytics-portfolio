from dataclasses import dataclass


@dataclass(frozen=True)
class Finding:
    """One problem in one output. Codes are stable, texts may change."""

    code: str
    text: str
    output: str = ""

    def __str__(self) -> str:
        where = f"[{self.output}] " if self.output else ""
        return f"{where}{self.code}: {self.text}"
