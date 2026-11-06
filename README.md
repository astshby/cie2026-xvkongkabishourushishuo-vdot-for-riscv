# CIE 2026：香山昆明湖V2的vdot扩展

参赛标识：`xvkongkabishourushishuo`。

## 提交位置

| 阶段 | 文档目录 | 视频目录 | 官网位置 |
| --- | --- | --- | --- |
| 一：环境部署与验证 | stages/01-environment/docs/ | stages/01-environment/videos/ | 第一阶段文档区、第一阶段操作过程录屏 |
| 二：vdot设计与实现 | stages/02-vdot/docs/ | stages/02-vdot/videos/ | 第二阶段设计及基础测试文档、解题思路讲解录屏 |
| 三：协同仿真与性能 | stages/03-verification/docs/ | stages/03-verification/videos/ | 第三阶段协同仿真及性能分析文档、波形与性能分析录屏 |

阶段一文档区提交两份文件：

- [操作过程.log](stages/01-environment/docs/操作过程.log)：从原始记录提取的实际终端操作日志，已去除终端颜色控制符。
- [向量加法执行过程分析.pdf](stages/01-environment/docs/向量加法执行过程分析.pdf)：由参赛者当前编辑的Word导出。

第一阶段已完成，保留可提交文件和原始验证记录。

第一阶段实际视频为[stage-1.mp4](stages/01-environment/videos/stage-1.mp4)。`stages/01-environment/原始验证记录.tar.gz`保留原始终端会话、构建输出、完整仿真日志和压缩精简波形；操作过程.log从其中的operations.log原样提取。

## 材料整理规则

- 过程分析使用Word编辑，由参赛者修改确认后再生成PDF。操作过程使用实际执行生成的log，不另写对应的Word文档。提交内容集中在要求的文件中，避免另设说明附件和文档间跳转。
- 正文、表格、命令和插图统一使用黑色，不加入日期、运行编号或录制时长。仿真周期作为实验数据保留。
- 视频有声讲解，不制作字幕。第二阶段讲解可按源码文件拆分，讲稿包含命令和逐段RTL说明；阶段结束后清理讲稿。
- 每次工作结束清除重复版本、预览、导出缓存和无用附件，保留源码、必要证据与当前编辑版本。
- 原始日志保留实际记录，不改写原始时间信息；归档后不重复展开存放。
- 第一阶段已整理为完整本地提交。第二、三阶段按顺序完成，代码、测试和日志随相应阶段保存。

## 运行程序

在本仓库根目录执行：

```bash
source scripts/env.sh
export KKS_IP_ADDRESS=192.168.230.128  # 使用实际虚拟机地址
bash scripts/build_app.sh hello
bash scripts/run_emu.sh hello baseline diff
```

基础源码和工具链位于同级xs-env，也可用XS_ENV指定。源码版本和工具版本在env/versions.json中记录，工程不依赖临时参考作品目录。源码位于tests/，运行脚本位于scripts/。

根目录LICENSE保留原有MIT许可；迁入文件的许可在NOTICE.md中说明。
