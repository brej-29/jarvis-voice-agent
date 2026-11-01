FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
RUN pip install "fastapi>=0.110,<1" "uvicorn>=0.27,<1" "httpx>=0.26,<1" "numpy>=1.26,<3" \
    "onnxruntime>=1.18,<2" "tokenizers>=0.19,<1" "dateparser>=1.2,<2"
COPY --chown=user jarvis ./jarvis
COPY --chown=user models/joint ./models/joint
USER user
ENV JARVIS_ALLOWED_HOSTS="*.hf.space,hf.space"
EXPOSE 7860
CMD ["python", "-m", "jarvis", "--host", "0.0.0.0", "--port", "7860", "--no-browser"]
