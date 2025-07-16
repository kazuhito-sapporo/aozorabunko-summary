# Pythonの公式イメージをベースにする
FROM python:3.9-slim-buster

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
# pipのキャッシュを無効にして、ビルドサイズを小さくする
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# Streamlitが使用するポートを公開
EXPOSE 8501

# アプリケーションを実行するコマンド
# Streamlitを直接実行し、ポート8501でリッスンするように設定
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
