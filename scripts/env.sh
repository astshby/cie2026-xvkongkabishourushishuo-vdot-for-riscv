#!/usr/bin/env bash
# 被其他脚本 source：变量均有项目专用前缀，不改动用户 HOME。
KKS_ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export XS_ENV=$(realpath -m -- "${XS_ENV:-$KKS_ROOT/../xs-env}")
export AM_HOME=$(realpath -m -- "${KKS_AM_HOME:-$XS_ENV/nexus-am}")
export NEMU_HOME="$XS_ENV/NEMU"
export NOOP_HOME="$XS_ENV/XiangShan"
export DRAMSIM3_HOME="$XS_ENV/DRAMsim3"
export KKS_XS="$KKS_ROOT/work/XiangShan"
export KKS_NEMU="$KKS_ROOT/work/NEMU"
export PATH="$KKS_ROOT/build/tools/bin:$PATH"
# 常见安装位置仅作为后备，优先使用调用者配置的工具链和 JAVA_HOME。
if ! command -v riscv64-unknown-linux-gnu-gcc >/dev/null && [[ -d /opt/riscv/bin ]]; then
  export PATH="$PATH:/opt/riscv/bin"
fi
if [[ -n "${JAVA_HOME:-}" ]]; then
  export JAVA_HOME=$(realpath -m -- "$JAVA_HOME")
  export PATH="$JAVA_HOME/bin:$PATH"
elif [[ -x /opt/graalvm-jdk-21/bin/java ]]; then
  export JAVA_HOME=/opt/graalvm-jdk-21
  export PATH="$JAVA_HOME/bin:$PATH"
fi
if [[ -z "${CROSS_COMPILE:-}" ]]; then
  if command -v riscv64-unknown-linux-gnu-gcc >/dev/null; then
    export CROSS_COMPILE=riscv64-unknown-linux-gnu-
  else
    export CROSS_COMPILE=riscv64-linux-gnu-
  fi
fi
if [[ "$CROSS_COMPILE" == */* && "$CROSS_COMPILE" != /* ]]; then
  export CROSS_COMPILE=$(realpath -m -- "$CROSS_COMPILE")
fi
export KKS_JOBS=${KKS_JOBS:-4}
# Mill缓存随本项目放入忽略的build目录；依赖仍使用同一Maven Central仓库。
export MILL_DOWNLOAD_PATH=$(realpath -m -- "${MILL_DOWNLOAD_PATH:-$KKS_ROOT/build/tools/mill}")
export COURSIER_REPOSITORIES=${COURSIER_REPOSITORIES:-https://repo.maven.apache.org/maven2}
if [[ -z "${CHISEL_FIRTOOL_PATH:-}" && -x "$KKS_ROOT/build/tools/firtool/firtool" ]]; then
  export CHISEL_FIRTOOL_PATH="$KKS_ROOT/build/tools/firtool"
elif [[ -n "${CHISEL_FIRTOOL_PATH:-}" ]]; then
  export CHISEL_FIRTOOL_PATH=$(realpath -m -- "$CHISEL_FIRTOOL_PATH")
fi
