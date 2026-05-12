from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import anthropic
import base64
import os
from PIL import Image
import io

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mirumiru-secret-2024')

# ユーザー設定（環境変数で上書き可能）
USERS = {
    os.environ.get('ADMIN_USER', 'satomi'): os.environ.get('ADMIN_PASS', 'admin2024'),
    os.environ.get('USER1', 'gaichuu1'): os.environ.get('PASS1', 'pass2024'),
    os.environ.get('USER2', 'gaichuu2'): os.environ.get('PASS2', 'pass2024'),
}
