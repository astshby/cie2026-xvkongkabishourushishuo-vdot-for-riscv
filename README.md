# CIE 2026：香山昆明湖 V2 的 vdot 扩展

参赛标识：`xvkongkabishourushishuo`。在昆明湖 V2 上实现 16 对 signed int8 点积，结果写入向量目的寄存器低 32 位、高 96 位清零。包含 Chisel RTL、香山接入补丁、NEMU 扩展、功能测试及实际性能数据。

## 三阶段提交材料

| 阶段 | 文档 | 有声视频 | 实际记录 |
| --- | --- | --- | --- |
| 一：环境部署与验证 | [操作过程.log](stages/01-environment/docs/操作过程.log)、[向量加法执行过程分析.pdf](stages/01-environment/docs/向量加法执行过程分析.pdf) | [stage-1.mp4](stages/01-environment/videos/stage-1.mp4) | [原始验证记录.tar.gz](stages/01-environment/原始验证记录.tar.gz) |
| 二：vdot 设计与实现 | [设计文档.pdf](stages/02-vdot/docs/设计文档.pdf)、[基础测试文档.pdf](stages/02-vdot/docs/基础测试文档.pdf) | [stage-2.mp4](stages/02-vdot/videos/stage-2.mp4) | [logs](stages/02-vdot/logs/) |
| 三：协同仿真与性能 | [协同仿真.pdf](stages/03-verification/docs/协同仿真.pdf)、[性能测试.pdf](stages/03-verification/docs/性能测试.pdf) | [stage-3.mp4](stages/03-verification/videos/stage-3.mp4) | [logs](stages/03-verification/logs/)、[waves](stages/03-verification/waves/)、[images](stages/03-verification/images/) |

三个阶段分别保存在 `stage1`、`stage2`、`stage3` 标签中；复现完整作品请使用 `stage3` 或当前 `main`。阶段一、二保留当时的完整材料与源码，下面的第三阶段命令用于最终版本。Word 经参赛者修改后导出 PDF；完成录制后清理讲稿与重复导出文件。日志保留原始记录，其中的本机绝对路径和时间属于历史运行信息，运行脚本不依赖这些路径。

## 首次配置环境

实测环境为 x86-64 Ubuntu 22.04、JDK 21、Mill 0.12.3、Chisel 6.6.0、firtool 1.62.1、Verilator 5.052。整核构建使用 4 个并行任务和 12G JVM 堆，本次虚拟机约 19GiB 内存、15GiB swap。磁盘需容纳依赖源码、编译缓存及临时整核 VCD。首次下载需要访问 GitHub、Maven Central 和工具安装脚本使用的软件源。

先克隆作品，再获取同级开发环境。源码目录使用不含空格的路径，上游 nexus-am 的 Makefile 无法处理空格路径。所有命令均使用当前用户自己的路径：

```bash
git clone https://github.com/astshby/cie2026-xvkongkabishourushishuo-vdot-for-riscv.git
cd cie2026-xvkongkabishourushishuo-vdot-for-riscv
export XS_ENV="$(cd .. && pwd)/xs-env"
git clone https://github.com/OpenXiangShan/xs-env.git "$XS_ENV"
git -C "$XS_ENV" checkout --detach cb1b5d9cc10dbc52677de4f9662e04bed69f2b2d
git -C "$XS_ENV" submodule update --init --recursive XiangShan NEMU nexus-am DRAMsim3
```

如果已有部署好的环境，跳过第二次克隆，执行 `export XS_ENV=/你的实际路径/xs-env`。推荐提交如下，全部原始版本和工具读数保存在 [env/versions.json](env/versions.json)：

| 源码 | 推荐提交 |
| --- | --- |
| xs-env | `cb1b5d9cc10dbc52677de4f9662e04bed69f2b2d` |
| XiangShan | `16ae9ddcda54fc9a2fddffad73174cf793ac7814` |
| NEMU | `a48a11f208ff81ad765591d83271d1b339fb3861` |
| nexus-am | `086a238062fdfb3281b745a537b361983d0154b5` |

使用其他提交时，准备脚本打印版本提示并继续。新建隔离工作树使用各基础仓库当前的 `HEAD`；已有隔离工作树保留其版本与修改。补丁不能应用、接口发生变化或测试失败时会实际报错，需要按该版本调整接入。NEMU 内部依赖的默认提交见 [nemu-dependencies.json](env/nemu-dependencies.json)，这是默认构建配置。切换整套基础版本时使用新的作品克隆目录，避免复用旧的工作树与构建缓存。

未安装工具时，在上述推荐 xs-env 中按目标安装。已有对应工具可跳过这些安装步骤：

```bash
(
  cd "$XS_ENV"
  sudo bash setup-tools.sh --target base
  sudo bash setup-tools.sh --target jdk
  sudo bash setup-tools.sh --target llvm
  sudo env PATH="/usr/local/llvm/bin:$PATH" bash setup-tools.sh --target verilator
)
sudo apt-get install -y ripgrep gtkwave python3-matplotlib fonts-noto-cjk fontconfig
mkdir -p build/tools/bin
curl -fL --retry 3 \
  https://repo.maven.apache.org/maven2/com/lihaoyi/mill-dist/1.0.4/mill-dist-1.0.4-mill.sh \
  -o build/tools/bin/mill
chmod +x build/tools/bin/mill
source scripts/env.sh
```

Mill 启动器读取香山的 `.mill-version`，使用 0.12.3。Chisel 首次生成 RTL 时获取对应 firtool；已有本地 firtool 时，可在 `source` 前设置 `CHISEL_FIRTOOL_PATH` 为包含 `firtool` 可执行文件的目录。本项目的缓存保存在忽略的 `build/`，不提交现成模拟器或工具二进制。

`env.sh` 优先采用调用者配置的 `JAVA_HOME`、`CROSS_COMPILE` 和 `PATH`。默认检测 `riscv64-unknown-linux-gnu-`，没有时采用安装脚本提供的 `riscv64-linux-gnu-`。使用其他位置的工具链可先设置 `export CROSS_COMPILE=/实际工具链/bin/riscv64-unknown-linux-gnu-`。修改并行任务和 JVM 堆可设置 `KKS_JOBS`、`KKS_JVM_XMX`。

## 阶段一：Hello 与向量加法

从作品仓库根目录执行。新环境先构建原始模拟器；已有原始模拟器可跳过第一条构建命令：

```bash
source scripts/env.sh
bash scripts/build_emu.sh baseline
# 自动检测实际 IPv4；也可先 export KKS_IP_ADDRESS=你的实际网卡地址。
bash scripts/build_app.sh hello
bash scripts/run_emu.sh hello baseline diff
bash scripts/build_app.sh vadd
bash scripts/run_emu.sh vadd baseline diff
```

Hello 输出 `hello xiangshan, I am xvkongkabishourushishuo, IP address: ...`。完整操作与向量波形采集脚本为 [stage1-run.sh](scripts/stage1-run.sh)，运行前按脚本提示指定实际 IP。默认基线参考库来自所选香山 `ready-to-run` 子模块。

## 阶段二：RTL 与基础功能

独立算术模块为 [VDot16.scala](rtl/VDot16.scala)，编码及配置检查为 [KksVDot.scala](rtl/KksVDot.scala)，译码和 VIPU 接入修改在 [xiangshan.patch](patches/xiangshan.patch)。构建脚本在忽略的 `work/` 创建隔离工作树，不修改基础 XiangShan 和 NEMU 的已跟踪源码；依赖子模块使用已初始化的源码。`nexus-am` 会生成常规编译缓存。

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

四项 Chisel 测试通过。整核点积测试完成 216 组输入、五种寄存器变体和 1080 次完整 128 位比较；连续依赖、VIPU 交错、分支跳过、八种非法配置与标准向量加法通过。`custom` 使用作品隔离目录构建的模拟器，`nodiff` 使用程序中的独立标量参考自检。此阶段的单元测试使用 Treadle，整核使用 Verilator。

## 阶段三：NEMU、DiffTest 与性能

NEMU 指令实现和启动/异常适配分别在 [nemu.patch](patches/nemu.patch)、[nemu-compat.patch](patches/nemu-compat.patch)。测试源码位于 `tests/nemu`、`tests/vdot`、`tests/illegal`、`tests/vadd`、`tests/bench`、`tests/smoke`，分别用于直接参考库测试、整核功能/异常、标准指令回归、性能采样和波形程序；它们用于复现提交结果，保留在仓库中。

已有匹配的自定义整核构建时可跳过 `build_emu.sh`。以下完整流程重新生成第三阶段日志、性能 JSON、精简波形和两幅图片，会更新对应提交材料：

```bash
source scripts/env.sh
bash scripts/build_emu.sh
bash scripts/stage3-run.sh
```

单独构建与快速检查 NEMU：

```bash
source scripts/env.sh
bash scripts/build_nemu.sh
python3 scripts/test_nemu.py
```

单独运行性能程序：

```bash
bash scripts/build_app.sh bench
KKS_TIMEOUT=3600 bash scripts/run_emu.sh bench custom diff
python3 scripts/analyze_stage3.py perf build/logs/bench-custom-diff.log
```

`diff` 明确加载本作品的 NEMU 共享库；运行前检查实际源码及产物的构建清单。清单根据本次编译生成，不绑定参赛者机器或提交号；源码改变后重新构建即可。单次运行原始日志写入 `build/logs`，第三阶段完整流程将其复制到正式 `logs`。只有进程退出码为 0 且出现 `GOOD TRAP` 才报告通过。

本次 NEMU 直接测试完成 665 次完整结果比较及八种异常检查。五个整核 DiffTest 程序全部通过。vdot 实测输入到输出两拍；32 次依赖链计算窗口为基线 1184 周期、vdot 480 周期，约 2.467 倍；完整调用窗口为 1363 与 659 周期，约 2.068 倍。原始 15 组样本与测量范围见性能文档和实际日志。其他工具或源码版本的周期结果可能变化，应使用新运行结果分析。

查看已提交的实际波形，无需重新构建：

```bash
source scripts/env.sh
gtkwave "$KKS_ROOT/stages/03-verification/waves/执行波形.vcd.gz" \
  --script="$KKS_ROOT/stages/03-verification/waves/view.tcl"
# 关闭前一窗口，再查看基线片段。
KKS_WAVE_VIEW=baseline gtkwave "$KKS_ROOT/stages/03-verification/waves/执行波形.vcd.gz" \
  --script="$KKS_ROOT/stages/03-verification/waves/view.tcl"
```

GTKWave 需要图形桌面；远程或无桌面环境可查看 `images/` 图片及 `waves/波形数据.json`。精简波形保留实际 152 个信号，完整大 VCD 在成功提取后自动删除。首次构建及首次运行记录压缩保存在日志目录，最终通过记录单独保留。

根目录 [LICENSE](LICENSE) 保留原有 MIT 许可；迁入文件及外部组件的许可说明见 [NOTICE.md](NOTICE.md)。
