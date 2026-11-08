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
- 视频有声讲解，不制作字幕。第二阶段使用一份解题思路讲稿，包含代码位置和简短测试命令；阶段结束后清理讲稿。
- 每次工作结束清除重复版本、预览、导出缓存和无用附件，保留源码、必要证据与当前编辑版本。
- 原始日志保留实际记录，不改写原始时间信息；归档后不重复展开存放。
- 第一、二阶段已整理为完整本地提交。第三阶段继续保存代码、测试和日志。

## 运行程序

在本仓库根目录执行：

```bash
source scripts/env.sh
export KKS_IP_ADDRESS=192.168.230.128  # 使用实际虚拟机地址
bash scripts/build_app.sh hello
bash scripts/run_emu.sh hello baseline diff
```

基础源码和工具链位于同级xs-env，也可用XS_ENV指定。源码版本和工具版本在env/versions.json中记录，工程不依赖临时参考作品目录。源码位于tests/，运行脚本位于scripts/。

## 第二阶段

第二阶段已完成，保留两份提交PDF，上传第二阶段文档区：

- [设计文档.pdf](stages/02-vdot/docs/设计文档.pdf)：指令语义、编码、位宽、两级数据通路、译码和VIPU接入。
- [基础测试文档.pdf](stages/02-vdot/docs/基础测试文档.pdf)：测试输入、参考算法、配置异常、操作命令和实际结果。

RTL源文件为[VDot16.scala](rtl/VDot16.scala)、[KksVDot.scala](rtl/KksVDot.scala)，接入修改为[xiangshan.patch](patches/xiangshan.patch)。本作品按16对signed int8实现。

在作品根目录执行：

```bash
source scripts/env.sh
bash scripts/test_chisel.sh
bash scripts/build_emu.sh
bash scripts/build_app.sh vdot
bash scripts/build_app.sh illegal
bash scripts/build_app.sh vadd
KKS_TIMEOUT=3600 bash scripts/run_emu.sh vdot custom nodiff
KKS_TIMEOUT=1800 bash scripts/run_emu.sh illegal custom nodiff
bash scripts/run_emu.sh vadd custom nodiff
```

`custom`使用本作品的新模拟器，运行前校验源码和构建产物。`nodiff`执行RTL中的C标量参考自检；NEMU扩展与DiffTest留在第三阶段。实际构建、单元测试和运行日志保存在[logs](stages/02-vdot/logs/)，重新运行的日志写入build/logs。

本次四项Chisel单元测试全部通过。整核点积完成216组输入、五种寄存器变体及1080次完整128位比较；33条连续依赖、VIPU交错、分支跳过、八种非法配置和标准向量加法回归均通过，三个整核程序均以GOOD TRAP、退出码0结束。

第二阶段实际视频为[stage-2.mp4](stages/02-vdot/videos/stage-2.mp4)，保留有声讲解，上传第二阶段解题思路讲解录屏位置。录制完成后已清理讲稿和完成导出的Word，代码、PDF、实际视频及验证日志保留。

根目录LICENSE保留原有MIT许可；迁入文件的许可在NOTICE.md中说明。
