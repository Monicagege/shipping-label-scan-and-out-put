# LabelDesk V3

创建人：Ezreal

FedEx / UPS / CEVA 标签识别。Python 本地 CPU OCR、PDF / ZIP 批量上传、可编辑结果、七列一键复制。

## 运行

Python 3.11–3.13 x64，`pip install -r requirements.txt`，然后 `python server.py`。打开 http://127.0.0.1:8765 。首次 OCR 会下载模型；请保持联网。模型下载后可以离线 OCR，邮编校验仍需联网。

## 网站状态

本仓库目前是 V3 源码，尚未部署在线服务。GitHub Pages 无法运行 server.py 和 OCR 后端；直接发布 web 目录会导致 /api/recognize 不可用。完整在线网站需要 Python 托管服务，或者重写为浏览器端 OCR。当前 server.py 只监听本机，不能直接作为公网生产服务。

未提交实际面单、收件人数据、虚拟环境或样本识别结果。

## 许可

OCR: RapidOCR / ONNX Runtime；条码: ZXing-C++。PyMuPDF 为 AGPL/商业许可。正式分发请遵守依赖许可。
