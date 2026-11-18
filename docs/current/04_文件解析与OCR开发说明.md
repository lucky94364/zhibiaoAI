# 文件解析与 OCR 开发说明

## 1. 输入与保存

文件上传后先保存不可变原件，生成 ID、sha256、逻辑版本和相对目录。source_kind 明确为 tender 或 material。前端目录选择失败时可用多文件上传，仍保留用户可见分类。

服务器只接受清理后的相对目录，存储实际使用 ID，不将文件名拼成任意磁盘路径。首版不支持 ZIP 导入，避免目录导入阻塞闭环；导出 ZIP 在 S11 实现。

支持 PDF、PNG/JPG；DOC/DOCX 取决于转换器能力。类型不支持或损坏时返回明确错误，原件和错误记录仍保留。首版上传大小用配置限制，界面显示实际限制。

## 2. 解析管线

```text
原件登记 → 页面准备 → 原生文字/表格提取 → 质量判断
                                   ├ 可用：保存来源块
                                   └ 不足：渲染/取图 → OCR → 保存来源块
→ 页面与文件对账 → 发布解析产物
```

有文字层不代表所有内容已经覆盖：混合 PDF 的扫描附件、图片表格和证书区域可能仍需 OCR。先以真实样本确定可解释的判断规则，记录每页采用的方法和遗漏风险。

## 3. 接口设计

```text
DocumentParser.parse(file_ref, options) -> ParsedDocument
OCRProvider.recognize(page_image, language, options) -> OCRPage
StoragePort.put/get/open/create_download_ref
```

输出映射到 SourceBlock，不直接把某第三方 SDK 对象存数据库。OCR 至少提供文字、页/图像身份和质量问题；坐标可取得时保存。

页索引从 1 开始；印刷页码是另一个可空字段。bbox 必须注明原点、单位、页面宽高和旋转，前端按同一图像缩放，不能直接混用 PDF 点坐标和像素。

## 4. Word 转换

探测 LibreOffice；没有转换器时 capabilities.converter=unavailable，DOC/DOCX 解析明确失败或提示先上传 PDF。

转换任务隔离工作目录，保留原件、转换 PDF、转换器版本和错误。来源定位到本次转换 PDF，页面预览也使用它，不承诺与其他软件的 Word 分页一致。

转换可后接，但公开样本为 DOC，因此真实样本扩展验收前必须完成一次受控转换及人工抽查。

## 5. 原文与结构

- 保存完整提取文字和页面图；摘要不能替代原文。
- 表格保留行列或可追溯行块，金额/单位/表头不能拆散到无法解释。
- 按章节、表格和长度分块，保留 file_id/page/section；重叠块记录关系，避免重复要求。
- 置信度来自引擎时保存，但不将高置信度等同于事实正确。
- 用户修订提取字段时保留原机器值；修订发布新产物版本并触发相关核验失效。

## 6. 失败和重试

逐页记录 planned/succeeded/failed。部分页失败时 file.parse_state=partial，任务记录失败及已完成产物；前端可以查看成功页，但相关不完整材料不能支撑 missing 或整项通过。

重新解析创建新 job 和新来源块。输出发布前检查文件仍是预期版本；旧来源块不删，旧结果可继续回看。

相同文件及解析配置可复用已成功产物；缓存键包含文件指纹、解析/OCR实现及配置版本。换引擎或修订规则不能错误命中旧缓存。

## 7. 真实 OCR 最小验证

使用 `../group_platform_materials_v1/samples/` 的：

1. 财务文字 PDF：能提取主体、2025 年度及模拟意见。
2. 无文字层过期证书 PDF：普通文字提取为空，真实 OCR 识别林明、所属单位及 2026-10-31。
3. 营业执照 PNG：提取主体与长期有效。
4. 补材证书 PNG：识别更新有效期，来源指向新文件。

PDF/图片是真实输入，不能只读取 expected_results.json 或同名预置字段通过此验收。OCR 未安装时记录 unavailable，真实 OCR 用例不得标 passed。

## 8. 实施依据

- [pdfplumber](https://github.com/jsvine/pdfplumber)：文字与表格。
- [pypdf 文字提取边界](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)：扫描件仍需 OCR。
- [pypdfium2](https://pypdfium2.readthedocs.io/en/stable/python_api.html)：渲染与线程约束，首版单 worker 顺序使用。
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)：验证兼容 Python/硬件的版本并锁定。
- [LibreOffice 参数](https://help.libreoffice.org/latest/en-US/text/shared/guide/start_parameters.html)：转换 DOC/DOCX。
