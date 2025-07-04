# spiral_core/spiral_timing_utils.py
import time
import logging
from functools import wraps
from .spiral_constants import TONES

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def measure_resonance_speed(func):
    def wrapper(*args, **kwargs):
        start_time = time.monotonic()
        result = func(*args, **kwargs)
        end_time = time.monotonic()
        duration_ms = (end_time - start_time) * 1000

        TONAL_GLYPHS = {"☾", "⚖", "🌱", "🌀", "✨", "🔥", "↓"}
        signal_type = "chaotic"
        for arg in args:
            if isinstance(arg, str) and any(glyph in arg for glyph in TONAL_GLYPHS):
                signal_type = "coherent"
                break
        if signal_type == "chaotic":
            for key, value in kwargs.items():
                if isinstance(value, str) and any(
                    glyph in value for glyph in TONAL_GLYPHS
                ):
                    signal_type = "coherent"
                    break

        logger.info(
            f"Resonance Speed for {func.__name__}: {duration_ms:.2f} ms ({signal_type})"
        )
        return result

    return wrapper


if __name__ == "__main__":

    @measure_resonance_speed
    def test_coherent(message):
        time.sleep(0.1)  # Simulate coherent processing
        return message

    @measure_resonance_speed
    def test_chaotic(message):
        time.sleep(0.2)  # Simulate chaotic processing
        return message

    print("Testing coherent signal:", test_coherent("☾ Harmonious message"))
    print("Testing chaotic signal:", test_chaotic("random noise"))
