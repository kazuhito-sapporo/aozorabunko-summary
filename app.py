import streamlit as st
import requests
import re
import nltk
import MeCab # MeCabをインポート
import unidic_lite # unidic-liteをインポートして辞書パスを取得
from bs4 import BeautifulSoup # BeautifulSoupをインポート
from urllib.parse import urljoin # urljoinは今回は不要ですが、残しておきます

from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer

import streamlit as st
import nltk

# NLTKデータのダウンロードをキャッシュする関数
# 修正前
# try:
#     nltk.data.find('corpora/punkt')
# except nltk.downloader.DownloadError:
#     nltk.download('punkt')

# 修正後
@st.cache_data
def download_nltk_data():
    try:
        nltk.data.find('corpora/punkt')
    except LookupError:
        nltk.download('punkt')

#    try:
        # 必要なデータをここでダウンロード
#        nltk.data.find('corpora/punkt')
#        nltk.data.find('corpora/stopwords')
#    except nltk.downloader.DownloadError:
        # ダウンロードされていない場合はダウンロード
#        nltk.download('punkt')
#        nltk.download('stopwords')

# アプリのメイン部分
def main():
    st.title("青空文庫要約アプリ")
    
    # NLTKデータをダウンロード
    download_nltk_data()

    # ... その他の処理
    # ... 例: ユーザー入力、モデルのロード、要約の実行など
    
if __name__ == '__main__':
    main()

# NLTKデータのダウンロード (初回のみ実行されるようにキャッシュ)
# Streamlit Cloudでは自動的にキャッシュされるため、毎回実行しても問題ありません。
#st.cache_resource
#def download_nltk_data():
    """
    NLTKの'punkt'トークナイザーデータをダウンロードします。
    sumyライブラリの動作に必要です。
    """
#    try:
#        nltk.data.find('tokenizers/punkt')
#    except nltk.downloader.DownloadError:
#        nltk.download('punkt', quiet=True)

# MeCabの初期化 (キャッシュして一度だけ行う)
@st.cache_resource
def init_mecab():
    """
    MeCab形態素解析器を初期化します。
    unidic-liteの辞書パスを明示的に指定します。
    """
    # unidic-liteの辞書パスを取得
    dicdir = unidic_lite.DICDIR
    
    # mecabrcファイルのパスを unidic-lite の dicdir にあるものに設定
    mecabrc_path = f"{dicdir}/mecabrc"

    # -rオプションでmecabrcのパスを指定し、-dオプションで辞書パスを指定
    return MeCab.Tagger(f"-r {mecabrc_path} -d {dicdir}")

# MeCabの初期化 (キャッシュして一度だけ行う)
#@st.cache_resource
#def init_mecab():
    """
    MeCab形態素解析器を初期化します。
    unidic-liteの辞書パスを明示的に指定します。
    """
    # unidic-liteの辞書パスを取得
#    dicdir = unidic_lite.DICDIR

    # -dオプションのみを渡し、mecabrcファイルの探索を省略
    # これにより、/usr/local/etc/mecabrc が存在しなくてもエラーにならない
#    return MeCab.Tagger(f"-d {dicdir}")

# MeCabの初期化 (キャッシュして一度だけ行う)
#@st.cache_resource
#def init_mecab():
    """
    MeCab形態素解析器を初期化します。
    unidic-liteの辞書パスを明示的に指定します。
    -Ochasenオプションは削除されています。
    """
    # unidic-liteの辞書パスを取得
 #   dicdir = unidic_lite.DICDIR
    # 辞書パスを-dオプションでMeCab.Taggerに渡す
    # -Ochasenオプションは削除し、デフォルトの出力形式を使用
 #   return MeCab.Tagger(f"-d {dicdir}")

# NLTKデータとMeCabの初期化を実行
download_nltk_data()
mecab_tagger = init_mecab() # MeCabタグ付けオブジェクトを初期化

# Streamlit UIのタイトルを設定
st.title("青空文庫 要約アプリ (品詞考慮版 - XHTMLエンコーディング修正済み)")

def clean_aozora_text(text):
    """
    青空文庫のテキストからルビや外字注記などの特殊記号を除去し、
    テキストを整形します。
    Args:
        text (str): 青空文庫から取得した生のテキスト。
    Returns:
        str: クリーンアップされたテキスト。
    """
    # ルビを削除（例: 漢字《かんじ》 -> 漢字）
    text = re.sub(r'《.*?》', '', text)
    # 外字注記を削除（例: ［＃外字］）
    text = re.sub(r'［＃.*?］', '', text)
    # 改行コードの調整と連続する改行の除去
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'\n\n+', '\n', text).strip()
    # 空白文字の正規化 (全角スペースなども半角に)
    text = re.sub(r'[ 　]+', ' ', text)
    return text

def analyze_pos(text):
    """
    MeCabを使ってテキストを形態素解析し、品詞情報を取得します。
    MeCabのデフォルト出力形式に対応しています。
    Args:
        text (str): 解析対象のテキスト。
    Returns:
        list: (単語, 品詞) のタプルのリスト。
    """
    # MeCabのデフォルト出力は、各行が「単語\t品詞,品詞細分類1,品詞細分類2,...」の形式
    parsed_lines = mecab_tagger.parse(text).split('\n')
    pos_data = []
    for line in parsed_lines:
        if line == 'EOS' or not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 2: # 少なくとも単語と品詞情報があることを確認
            word = parts[0]
            # 品詞情報は2番目の要素（インデックス1）にあり、カンマで区切られている
            pos_info = parts[1].split(',')[0] # 最も大分類の品詞を取得
            pos_data.append((word, pos_info))
    return pos_data

# ユーザーからの青空文庫URL入力を受け付けるテキストボックス
# 例としてXHTML版のURLを提示
aozora_url = st.text_input("青空文庫の作品URLを入力してください (例: https://www.aozora.gr.jp/cards/000879/files/40_15151.html)")

# 要約する文の数をユーザーが選択できるようにするスライダー
num_sentences = st.slider("要約する文の数", min_value=1, max_value=20, value=5)

# 要約実行ボタン
if st.button("要約する"):
    # URLが入力されているか確認
    if aozora_url:
        with st.spinner("XHTMLコンテンツ取得中..."):
            try:
                # 1. 入力されたURLからXHTMLコンテンツを直接取得
                response_xhtml = requests.get(aozora_url)
                response_xhtml.raise_for_status() # HTTPエラーをチェック
                
                # 青空文庫のXHTMLはShift_JISエンコーディングの場合が多いので、明示的にデコード
                # errors='ignore'を追加して、デコードできない文字があっても処理を続行
                try:
                    html_content = response_xhtml.content.decode('shift_jis', errors='ignore')
                except UnicodeDecodeError:
                    # Shift_JISでデコードできなかった場合、UTF-8を試す (念のため)
                    html_content = response_xhtml.content.decode('utf-8', errors='ignore')
                    st.warning("Shift_JISでデコードできませんでした。UTF-8で試行しました。")
                
                # BeautifulSoupでHTMLを解析し、純粋なテキストを抽出
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # 青空文庫のXHTMLは、本文が特定のdivタグ内にあることが多いです。
                # 例えば、<div class="main_text"> のような構造。
                # まず、本文と思われる要素を探します。
                main_text_div = soup.find('div', class_='main_text')
                if main_text_div:
                    raw_text = main_text_div.get_text()
                else:
                    # もし特定の本文divが見つからない場合、ページ全体のテキストを取得
                    raw_text = soup.get_text() 
                
                # 取得したテキストをクリーンアップ (青空文庫特有の記号除去)
                cleaned_text = clean_aozora_text(raw_text)

                # クリーンアップ後のテキストが空の場合の警告
                if not cleaned_text or len(cleaned_text.strip()) < 50: # 短すぎるテキストも対象外
                    st.warning("取得したテキストが空か、処理後に内容がありませんでした。または、要約できるほど十分な長さのテキストではありませんでした。")
                    st.stop() # 処理を停止

                # 取得したテキストの一部を表示
                st.subheader("取得したテキストの一部")
                # 長すぎるテキストは表示を制限し、スクロール可能なテキストエリアで表示
                display_text = cleaned_text[:1000] + ("..." if len(cleaned_text) > 1000 else "")
                st.text_area("元のテキスト", display_text, height=200, key="original_text_area")

                # 品詞解析のデモンストレーション
                st.subheader("品詞解析の例 (上位20単語)")
                pos_results = analyze_pos(cleaned_text)
                # 品詞情報を含む単語を整形して表示
                pos_display = "\n".join([f"{word} ({pos})" for word, pos in pos_results[:20]])
                st.text_area("品詞解析結果", pos_display, height=150, key="pos_analysis_area")
                st.info("※この品詞解析結果は、要約アルゴリズムに直接利用されているわけではありませんが、より高度な要約を実装する際の基礎となります。")


                with st.spinner("要約中..."):
                    # sumyライブラリのPlaintextParserでテキストを解析
                    # Tokenizer("japanese")で日本語の文分割を試みる
                    parser = PlaintextParser.from_string(cleaned_text, Tokenizer("japanese"))
                    # TextRankSummarizerを初期化
                    summarizer = TextRankSummarizer()
                    # 指定された文の数で要約を生成
                    summary = summarizer(parser.document, sentences_count=num_sentences)
                    # 要約された文を結合して一つの文字列にする
                    summarized_text = "".join([str(sentence) for sentence in summary])

                    # 要約結果が空の場合の警告
                    if not summarized_text:
                        st.warning("要約を生成できませんでした。テキストが短すぎるか、内容が要約に適していません。")
                    else:
                        # 要約結果を表示
                        st.subheader("要約結果")
                        st.success(summarized_text)

            except requests.exceptions.MissingSchema:
                st.error("無効なURL形式です。'http://' または 'https://' で始まる完全なURLを入力してください。")
            except requests.exceptions.RequestException as e:
                st.error(f"URLからのテキスト取得中にエラーが発生しました: {e}")
            except Exception as e:
                st.error(f"要約処理中に予期せぬエラーが発生しました: {e}")
    else:
        st.warning("URLを入力してください。")

# アプリのフッターと使い方ガイド
st.markdown("""
---
**使い方:**
1.  青空文庫の作品ページのXHTML版URLを上の入力欄に貼り付けます。
2.  「要約する文の数」スライダーで、要約の長さを調整します。
3.  「要約する」ボタンをクリックします。
4.  元のテキストの一部、品詞解析の例、そして要約結果が表示されます。

**注意点:**
* 要約の精度は、元のテキストの内容や長さ、選択された要約アルゴリズムに依存します。
* 非常に短いテキストや、特殊な形式のテキストはうまく要約できない場合があります。
* このアプリは`sumy`ライブラリの`TextRankSummarizer`を使用しています。
* 品詞解析は`MeCab`を使用していますが、現在の要約アルゴリズム（TextRank）に直接組み込まれているわけではありません。品詞情報を利用したより高度な要約には、別のアルゴリズムやカスタム実装が必要です。
""")
