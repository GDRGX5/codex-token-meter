# Uploading this folder to GitHub

This folder is already arranged as the root of a GitHub repository. Upload its
contents, not the `codex-token-meter-github` folder itself. `README.md`,
`LICENSE`, and `chatgpt_usage.py` should appear at the top level of the repo.

## Upload through the GitHub website

1. Create a new empty repository, such as `codex-token-meter`.
2. Leave the README, `.gitignore`, and license options unchecked.
3. Open the new repository and choose **Add file → Upload files**.
4. Drag everything from this folder into the upload area. Include `.github`,
   `.gitignore`, and `.gitattributes`.
5. Commit the upload.

GitHub Actions will run the test suite on Windows, macOS, and Linux after the
first commit.

## Upload from a terminal

Run these commands from inside this folder:

```bash
git init
git add .
git commit -m "Initial release"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/codex-token-meter.git
git push -u origin main
```

Replace `YOUR-NAME` with your GitHub username. The repository must already
exist before running the final two commands.

## 中文提示

這個資料夾已經是 repository 的根目錄。請上傳「資料夾裡面的全部內容」，不要只把
外層 `codex-token-meter-github` 當成一個子資料夾上傳。完成後，GitHub 首頁應直接
看到 `README.md`、`LICENSE` 與 `chatgpt_usage.py`。
