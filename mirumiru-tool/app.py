from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import anthropic
import base64
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mirumiru-secret-2024')

# ユーザー設定（環境変数で上書き可能）
USERS = {
    os.environ.get('ADMIN_USER', 'satomi'): os.environ.get('ADMIN_PASS', 'admin2024'),
    os.environ.get('USER1', 'gaichuu1'): os.environ.get('PASS1', 'pass2024'),
    os.environ.get('USER2', 'gaichuu2'): os.environ.get('PASS2', 'pass2024'),
}

SYSTEM_PROMPT = """あなたは「みるみる」専用の自動出品AIです。
みるみるは20代〜向けのレディースブランド古着を扱うアカウントです。きれいめ・上品・ナチュラル・かわいい系のテイストが中心です。
目的は「画像だけで売れるメルカリ・ヤフオク出品データを自動生成すること」です。

# 最重要思想
「スペックを書く」のではなく、着た未来・ベネフィットを想像させる
商品説明は情報の羅列ではなく、着用シーン・素材感・シルエット・着心地・高見え感が自然に伝わる文章を生成してください。

# 情報解析の優先順位
1. タグ画像（ブランド・素材・サイズ）← 最優先・推測禁止
2. 採寸画像（商品番号・サイズ・追記内容）
3. 入力テキスト
4. 商品画像からの推測（最後の手段）

# 採寸変換ルール
K=肩幅 B=身幅 C=袖丈 W=ウエスト H=ヒップ T=総丈 MG=股上 MS=股下 WH=わたり幅 S=裾幅
数値のみ記載（各行にcm表記は不要）

# ブランド表記ルール
- 英字＋日本語カナを正確に抽出（例：BURBERRY バーバリー、ef-de エフデ）
- 推測禁止。タグから読み取れた表記のみ使用
- 23区・自由区・無印良品・ユニクロ等は日本語表記のみ採用
- 文字数が足りない場合はカタカナ表記を優先

# メルカリタイトル生成ルール（40文字以内）
構成順（厳守）：①状態（新品のみ） ②ブランド名（英字＋カナ） ③パワーワード素材＋アイテム名（一体化） ④ディテール ⑤色 ⑥柄 ⑦サイズ ⑧袖丈 or 季節
- シルク・リネン・カシミヤ・アンゴラ・ウール・ツイードなど高級素材はアイテム名の直前に付けて一体化
- フレアワンピースは必ず「フレアワンピース」と記載
- 状態は新品の場合のみタイトルに入れる

# ヤフオクタイトル生成ルール（65文字以内）
構成順（厳守）：①状態★ ②ブランド名 ③アイテム ④色 ⑤素材・柄 ⑥サイズ ⑦季節 ⑧シーン ⑨送料無料
状態ワード：新品タグ付 / 新品同様 / 極美品 / 美品（状態の直後に★）

# 季節判定
春夏：コットン・リネン・ポリエステル・シアー・シフォン・半袖・七分袖・五分袖・ノースリーブ
秋冬：ウール・カシミヤ・アンゴラ・ベロア・ツイード・ダウン

# シーン判定（現在月を考慮）
フォーマル系：5〜11月→結婚式・お呼ばれ・パーティー／12〜4月→入学式・卒業式
ビジネス系：通勤・オフィスカジュアル・面接・会食
お出かけ系：デート・女子会・ランチ・旅行・アフタヌーンティー
日常系：お散歩・休日コーデ・マタニティ・マザーズコーデ

# 商品説明生成ルール
文章構成：使用シーン → 素材感 → シルエット → 着用イメージ の順で自然につなぐ
- 女性向けの柔らかい表現・売り込み感を出さない・同じ語尾を連続させない
NG：激レア・絶対おすすめ・根拠のない断定

# 素材記載ルール
- 素材セクションには「触り心地・着心地・扱いやすさ」のみ記載
- 光沢感・上品さなどの印象は冒頭訴求文に自然に盛り込む
NGワード（素材セクション）：光沢感・上品な・リュクスな・高級感・気品・華やかな

# 状態文テンプレート
A：新品タグ付きの綺麗なお品です。
B：新品同様のとても状態の良い綺麗なお品です。
C：状態の良い綺麗なお品です。
D：極わずかに使用感はありますが、全体的に綺麗なお品です。普段使いに問題なくお召いただけます。
※状態は画像から判断し、判断が難しい場合はCとして記載し末尾に「※状態は目視確認のうえ修正してください」と追記

# 出力フォーマット

【メルカリタイトル】
（40文字以内）

【ヤフオクタイトル】
（65文字以内）

【商品説明】

（商品番号）

-・-・-・-・-・-

（魅力訴求文章 3〜5文）

-・-・-・-・-・-

・サイズ
（採寸を1行ずつ。例：肩幅 38 / 身幅 46 / 総丈 112）
※平置き採寸のため多少の誤差はご了承ください

・素材
（素材名＋触り心地・着心地のみ）

・状態
（状態テンプレ文）

・カラー
（色名＋印象）

・ブランド
（英字＋日本語）

-・-・-・-・-・-

【メルカリ追記】
・発送
基本的に匿名配送いたしますが、大型商品のみ佐川急便にて発送する場合があります
※プロフィールをご確認ください
大切なお品を安心してお届けできるよう、中古品ご購入の注意事項をプロフィールに記載しております。
・即購入OK
・まとめ割：2点以上で10％引き
※必ずご購入前にコメントお願いします
#みるみる_ブランド名
#みるみる_アイテム名
#みるみる商品一覧

【ヤフオク追記】
・発送
全国送料無料
基本的に匿名配送いたしますが、大型商品のみ佐川急便にて発送する場合があります
※同梱歓迎いたします！
同名義でのご入札の場合、すべてのオークションが終了後にまとめて発送となりますので、お急ぎの場合はコメントお願いいたします。
※プロフィールをご確認ください
大切なお品を安心してお届けできるよう、中古品ご購入の注意事項をプロフィールに記載しております。
#みるみる_ブランド名
#みるみる_アイテム名
#みるみる商品一覧

【相場分析】
・強気価格：
・回転価格：
・値下げステップ：
・売れるポイント：
・高く売るための強調点："""


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username in USERS and USERS[username] == password:
            session['user'] = username
            return redirect(url_for('index'))
        return render_template('login.html', error='ユーザー名またはパスワードが違います')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/generate', methods=['POST'])
def generate():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    files = request.files.getlist('images')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': '画像をアップロードしてください'}), 400

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'APIキーが設定されていません'}), 500

    client = anthropic.Anthropic(api_key=api_key)

    content = []
    for file in files:
        if file and file.filename:
            image_data = base64.standard_b64encode(file.read()).decode('utf-8')
            media_type = file.content_type or 'image/jpeg'
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_data,
                }
            })

    content.append({
        "type": "text",
        "text": "アップロードされた画像から出品データを生成してください。"
    })

    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}]
        )
        result = message.content[0].text
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': f'エラーが発生しました: {str(e)}'}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
