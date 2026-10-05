"""Echte Video-Frames als Kontaktbogen kontrollieren; keine neue Modellbewertung."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main(video, ziel):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ausgabe/werkzeuge'))
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    Path(ziel).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(video),
                    '-vf', 'fps=1/4,scale=270:480,tile=6x4:padding=4:margin=4',
                    '-frames:v', '1', str(ziel)], check=True)
    print('Echte Frames im 4-Sekunden-Abstand:', ziel)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('video', type=Path)
    p.add_argument('ziel', type=Path)
    a = p.parse_args()
    main(a.video, a.ziel)
