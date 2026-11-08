#!/usr/bin/env bash
# 被其他脚本 source：变量均有项目专用前缀，不改动用户 HOME。
KKS_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export XS_ENV=${XS_ENV:-"$(cd "$KKS_ROOT/../xs-env" && pwd)"}
export AM_HOME="$XS_ENV/nexus-am"
export NEMU_HOME="$XS_ENV/NEMU"
export NOOP_HOME="$XS_ENV/XiangShan"
export DRAMSIM3_HOME="$XS_ENV/DRAMsim3"
export KKS_XS="$KKS_ROOT/work/XiangShan"
export KKS_NEMU="$KKS_ROOT/work/NEMU"
export CROSS_COMPILE=${CROSS_COMPILE:-riscv64-unknown-linux-gnu-}
export PATH="/opt/riscv/bin:/opt/graalvm-jdk-21/bin:$PATH"
export KKS_JOBS=${KKS_JOBS:-4}
# Mill缓存随本项目放入忽略的build目录；依赖仍使用同一Maven Central仓库。
export MILL_DOWNLOAD_PATH=${MILL_DOWNLOAD_PATH:-"$KKS_ROOT/build/tools/mill"}
export COURSIER_REPOSITORIES=${COURSIER_REPOSITORIES:-https://repo.maven.apache.org/maven2}
if [[ -z "${CHISEL_FIRTOOL_PATH:-}" && -x "$KKS_ROOT/build/tools/firtool/firtool" ]]; then
  export CHISEL_FIRTOOL_PATH="$KKS_ROOT/build/tools/firtool"
fi
