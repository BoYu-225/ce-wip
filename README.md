# 论文编译

主文件为 `ce.tex`，正文通过 `\input` 引入 `sections/` 和 `appendices/` 下的文件。

安装 TeX Live 或 MacTeX，确保 `pdflatex` 和 `bibtex` 在 `PATH` 中，然后运行：

```bash
./build.sh
```

脚本依次执行 `pdflatex → bibtex → pdflatex → pdflatex`，生成参考文献并解析交叉引用。也可以从其他目录通过脚本的绝对路径调用。

- 最终论文：`output/pdf/ce.pdf`
- 中间文件及各轮编译日志：`build/`
- 最后一轮 LaTeX 日志：`build/ce.log`

编译出错时脚本立即退出并打印错误日志末尾；所有步骤成功后才更新最终 PDF。
