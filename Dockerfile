FROM tensorflow/tensorflow:2.4.1-gpu

WORKDIR /app

RUN apt update
RUN apt install -y libgl-dev

RUN python3 -m pip install opencv-python
RUN python3 -m pip install Pillow
COPY . ./
