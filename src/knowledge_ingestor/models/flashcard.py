from dataclasses import dataclass


@dataclass
class Flashcard:
    question: str = ""
    answer: str = ""
