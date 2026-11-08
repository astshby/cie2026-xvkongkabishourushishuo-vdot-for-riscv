// SPDX-License-Identifier: MulanPSL-2.0
package xiangshan.backend.decode

import chisel3._
import chisel3.util.BitPat
import xiangshan.backend.fu.vector.VDot16Layout

/** 实验指令编码与支持范围集中定义，译码和配置测试使用同一份定义。 */
object KksVDot {
  val Opcode = 0x57
  val Funct6 = 0x03
  val DecodeMatch = BigInt("0c000057", 16)
  val DecodeMask = BigInt("fc00707f", 16)
  val UnmaskedMatch = BigInt("0e000057", 16)
  val UnmaskedMask = BigInt("fe00707f", 16)

  // funct3=000限定OPIVV；vm保留通配，masked形式由配置检查报告异常。
  def instruction: BitPat = BitPat("b000011???????????000?????1010111")
  def opType: UInt = "h0fe".U(9.W)

  // 此函数接输出级配置，不能拿当前输入去判断先前指令的数据。
  def unsupported(vill: Bool, sew: UInt, lmul: UInt, vl: UInt,
                  vstart: UInt, vm: Bool): Bool =
    vill || sew =/= 0.U || lmul =/= 0.U ||
      vl =/= VDot16Layout.Lanes.U || vstart =/= 0.U || !vm
}
