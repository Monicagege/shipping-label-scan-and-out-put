# LabelDesk · Ezreal

## GitHub 浏览器版

网站：https://monicagege.github.io/shipping-label-scan-and-out-put/

独立源码位于 pages/，由 .github/workflows/pages.yml 自动部署。首次发布需等待 Actions 成功；如 configure-pages 无权自动启用，请到 Settings → Pages → Source 选择 GitHub Actions 后重新运行工作流。

浏览器 OCR 使用 Tesseract.js，与本地 V3 的 RapidOCR 是不同引擎。PDF、ZIP 文件在浏览器内处理，支持 UPS 1Z、CEVA AZN 和 FedEx 数字单号、SHIP TO 区域提取、编辑与七列复制。首次需要联网下载 CDN 脚本和英文模型；城市/州/邮编通过 Zippopotam.us 查询。浏览器版尚未完成真实样本 OCR 回归与浏览器人工测试，结果必须核对。

## 本地 V3

本地 V3 交付包保持不变。根目录 engine.py、server.py 和 web/ 是独立 Python 版源码，不参与 Pages 发布。

本仓库没有实际面单、收件人测试结果或 Python 虚拟环境。

## 依赖许可

浏览器版：Tesseract.js / Tesseract、PDF.js（Apache-2.0）、JSZip（MIT/GPL 双许可）。本地版另使用 RapidOCR、ONNX Runtime、ZXing-C++ 和 PyMuPDF（AGPL/商业许可）。分发请遵守依赖许可。
