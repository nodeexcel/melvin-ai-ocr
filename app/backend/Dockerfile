FROM python:3.11.0-slim

RUN apt-get update && apt-get install -y \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /backend

COPY requirements.txt .
# Install PaddlePaddle from official mirror first, then pin it so paddleocr cannot override
RUN pip install --no-cache-dir paddlepaddle==3.2.0 \
    -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ && \
    echo "paddlepaddle==3.2.0" > /tmp/paddle_constraints.txt
RUN pip install --no-cache-dir -r requirements.txt -c /tmp/paddle_constraints.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8037"]
