from machine import Pin, PWM
import time

class Buzzer():
    def __init__(self, pin=18):
        self.buzzer = PWM(Pin(pin))
        self.buzzer.duty_u16(0)  # Start with the buzzer off

    def _play_tone(self, frequency, duration):
        """Play a tone at the specified frequency for the given duration."""
        self.buzzer.freq(frequency)
        self.buzzer.duty_u16(30000)  # Set duty cycle to 50%
        time.sleep_ms(duration)
        self.buzzer.duty_u16(0)  # Turn off the buzzer

    def boot_tone(self):
        """Play a cheerful boot melody when the robot starts."""
        # Ascending "ready to go" melody
        tones = [1000, 1200, 1500, 1500]
        for freq in tones:
            self._play_tone(freq, 200)  # Play each tone for 200ms
            time.sleep_ms(50)  # Short pause between tones

    def move_forward_tone(self):
        """Play a tone when the robot moves forward."""
        self._play_tone(800, 200)  # 800Hz for 200ms

    def stop_tone(self):
        """Play a tone when the robot stops."""
        self._play_tone(500, 300)  # 500Hz for 300ms

    def obstacle_detected_tone(self):
        """Play a tone when the robot detects an obstacle."""
        for _ in range(3):
            self._play_tone(2000, 100)  # 2kHz for 100ms
            time.sleep_ms(100)

    def turn_detected_tone(self):
        """Play a tone when the robot detects a turn."""
        self._play_tone(1200, 300)  # 1.2kHz for 300ms
        time.sleep_ms(100)
        self._play_tone(1200, 300)  # 1.2kHz for 300ms

    def emergency_stop_tone(self):
        """Play a 'computer failing' melody when the robot is stopped."""
        # Descending "error" melody
        tones = [1500, 1200, 1000, 800, 600, 400]
        for freq in tones:
            self._play_tone(freq, 200)  # Play each tone for 200ms
            time.sleep_ms(50)  # Short pause between tones
    
    def error_tone(self):
        """Play an error sound."""
        # Play a sequence of tones that sound like an error
        tones = [2000, 1000, 2000, 1000]
        for freq in tones:
            self._play_tone(freq, 150)  # Play each tone for 150ms
            time.sleep_ms(100)  # Short pause between tones
    
    def box_detect(self):
        """Play a sound when a box is detected/perceived by the robot."""
        tones = [500]
        for freq in tones:
            self._play_tone(freq, 200)
            time.sleep_ms(100)

    def nid_tone(self):
        """Play a short beep for the nest."""
        self._play_tone(1800, 100)

# Example usage:
if __name__ == "__main__":
    buzzer = Buzzer()
    # Test all tones

    print("Test: box detected.")
    buzzer.box_detect()
    time.sleep(1)

    print("Test: boot tone (cheerful)")
    buzzer.boot_tone()
    time.sleep(1)

    print("Test: moving tone")
    buzzer.move_forward_tone()
    time.sleep(1)

    print("Test: stop tone")
    buzzer.stop_tone()
    time.sleep(1)

    print("Test: obstacle tone")
    buzzer.obstacle_detected_tone()
    time.sleep(1)

    print("Test: turning tone")
    buzzer.turn_detected_tone()
    time.sleep(1)

    print("Test: emergency stop tone")
    buzzer.emergency_stop_tone()
