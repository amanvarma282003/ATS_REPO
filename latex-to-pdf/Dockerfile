FROM texlive/texlive:latest

# Install Python and pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Install FastAPI stack (system-wide)
RUN pip install --no-cache-dir --break-system-packages fastapi uvicorn python-multipart

WORKDIR /app
COPY app.py /app

EXPOSE 8006
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8006"]
