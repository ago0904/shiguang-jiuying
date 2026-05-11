#!/usr/bin/env python3
"""
拾光旧影 - GitHub一键上传脚本
用法: python github-push.py
"""
import os
import sys
import subprocess
import json
import getpass
import urllib.request
import urllib.error


def run_cmd(cmd, cwd=None):
    """运行命令"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr


def check_git():
    """检查git是否可用"""
    ok, out, err = run_cmd("git --version")
    if ok:
        print(f"✅ Git已安装: {out.strip()}")
        return True
    print("❌ Git未安装，请先安装Git: https://git-scm.com/downloads")
    return False


def get_github_credentials():
    """获取GitHub凭证"""
    print("\n" + "=" * 50)
    print("🔐 GitHub认证信息")
    print("=" * 50)
    print("\n你需要一个GitHub Personal Access Token (PAT)")
    print("获取方式:")
    print("1. 打开 https://github.com/settings/tokens")
    print("2. 点击 'Generate new token (classic)'")
    print("3. 勾选 'repo' 权限")
    print("4. 点击 Generate token")
    print("5. 复制生成的token\n")
    
    username = input("GitHub用户名: ").strip()
    token = getpass.getpass("GitHub Token (输入时不会显示): ").strip()
    
    return username, token


def verify_token(username, token):
    """验证token是否有效"""
    req = urllib.request.Request(
        "https://api.github.com/user",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("login") == username:
                print(f"✅ 认证成功! 欢迎, {data.get('name') or username}")
                return True
            else:
                print(f"⚠️ 用户名不匹配，API返回的用户是: {data.get('login')}")
                return False
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("❌ Token无效或已过期")
        else:
            print(f"❌ 验证失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return False


def create_repo(username, token, repo_name, description, is_private):
    """创建GitHub仓库"""
    print(f"\n📦 创建仓库 '{repo_name}'...")
    
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=json.dumps({
            "name": repo_name,
            "description": description,
            "private": is_private,
            "auto_init": False
        }).encode(),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            print(f"✅ 仓库创建成功!")
            print(f"   URL: {data['html_url']}")
            return data['clone_url'], True
    except urllib.error.HTTPError as e:
        if e.code == 422:
            error_body = json.loads(e.read().decode())
            for err in error_body.get("errors", []):
                if err.get("message") == "name already exists on this account":
                    print(f"⚠️ 仓库 '{repo_name}' 已存在，将推送到已有仓库")
                    return f"https://github.com/{username}/{repo_name}.git", False
            print(f"❌ 创建失败: {error_body}")
        else:
            print(f"❌ 创建失败: {e}")
        return None, False
    except Exception as e:
        print(f"❌ 网络错误: {e}")
        return None, False


def setup_git_and_push(project_dir, username, token, repo_url):
    """设置git并推送代码"""
    print("\n🚀 准备推送代码...")
    
    # 使用token认证URL
    auth_url = repo_url.replace("https://", f"https://{username}:{token}@")
    
    # 检查是否已初始化git
    git_dir = os.path.join(project_dir, ".git")
    if not os.path.exists(git_dir):
        print("📁 初始化Git仓库...")
        ok, _, err = run_cmd("git init", cwd=project_dir)
        if not ok:
            print(f"❌ git init 失败: {err}")
            return False
    
    # 配置git用户信息（如果没设置）
    ok, out, _ = run_cmd("git config user.name", cwd=project_dir)
    if not out.strip():
        run_cmd(f"git config user.name '{username}'", cwd=project_dir)
    
    ok, out, _ = run_cmd("git config user.email", cwd=project_dir)
    if not out.strip():
        run_cmd(f"git config user.email '{username}@users.noreply.github.com'", cwd=project_dir)
    
    # 检查remote
    ok, out, _ = run_cmd("git remote get-url origin", cwd=project_dir)
    if not ok:
        print("🔗 添加远程仓库...")
        run_cmd(f"git remote add origin {auth_url}", cwd=project_dir)
    else:
        print("🔄 更新远程仓库地址...")
        run_cmd(f"git remote set-url origin {auth_url}", cwd=project_dir)
    
    # 添加文件
    print("📥 添加文件到暂存区...")
    ok, _, err = run_cmd("git add -A", cwd=project_dir)
    if not ok:
        print(f"❌ git add 失败: {err}")
        return False
    
    # 提交
    print("💾 提交代码...")
    ok, _, err = run_cmd("git commit -m 'feat: init project - 拾光旧影 AI老照片修复小程序'", cwd=project_dir)
    if not ok:
        # 可能已经提交过
        print("⚠️ 可能已提交过，继续推送...")
    
    # 设置分支并推送
    print("📤 推送到GitHub...")
    run_cmd("git branch -M main", cwd=project_dir)
    ok, out, err = run_cmd("git push -u origin main --force", cwd=project_dir)
    if not ok:
        print(f"❌ 推送失败: {err}")
        return False
    
    return True


def main():
    print("=" * 50)
    print("🚀 拾光旧影 - GitHub一键上传")
    print("=" * 50)
    
    # 检查git
    if not check_git():
        sys.exit(1)
    
    # 项目目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = script_dir
    
    print(f"📂 项目目录: {project_dir}")
    
    # 获取凭证
    username, token = get_github_credentials()
    if not username or not token:
        print("❌ 用户名和Token不能为空")
        sys.exit(1)
    
    # 验证token
    print("\n🔍 验证Token...")
    if not verify_token(username, token):
        sys.exit(1)
    
    # 仓库设置
    print("\n" + "=" * 50)
    print("⚙️ 仓库设置")
    print("=" * 50)
    
    default_name = "shiguang-jiuying"
    repo_name = input(f"仓库名称 (默认: {default_name}): ").strip() or default_name
    
    default_desc = "拾光旧影 - AI老照片修复小程序，支持黑白上色、破损修复、清晰度增强、智能去噪"
    description = input(f"仓库描述 (默认: {default_desc}): ").strip() or default_desc
    
    is_private = input("设为私有仓库? (y/n, 默认: n): ").strip().lower() == "y"
    
    # 创建仓库
    result = create_repo(username, token, repo_name, description, is_private)
    if not result[0]:
        sys.exit(1)
    
    repo_url, is_new = result
    
    # 推送代码
    success = setup_git_and_push(project_dir, username, token, repo_url)
    
    if success:
        print("\n" + "=" * 50)
        print("🎉 上传成功!")
        print("=" * 50)
        print(f"\n📦 仓库地址: https://github.com/{username}/{repo_name}")
        print(f"🔗 Git URL: {repo_url}")
        print("\n📋 接下来你可以:")
        print("  1. 用微信开发者工具导入 miniprogram/ 目录")
        print("  2. 部署后端服务 (见 backend/DEPLOY.md)")
        print("  3. 配置小程序服务器域名")
        print("\n⚠️ 安全提示: 建议上传完成后删除本地token缓存")
        print("=" * 50)
    else:
        print("\n❌ 上传失败，请检查错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
