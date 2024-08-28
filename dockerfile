# Используем официальный образ Python в качестве базового образа
FROM python:3.11-slim

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Устанавливаем необходимые зависимости
RUN apt-get update && apt-get install -y ffmpeg libav-tools

# Проверяем установку ffmpeg
RUN ffmpeg -version

# Копируем файлы requirements.txt и setup.py в контейнер
COPY requirements.txt requirements.txt

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта в контейнер
COPY . .

# Указываем команду для запуска приложения
CMD ["python", "main.py"]