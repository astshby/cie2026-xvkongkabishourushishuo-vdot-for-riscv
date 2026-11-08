package xiangshan

import circt.stage.ChiselStage
import xiangshan.backend.fu.vector.VDot16

/** 生成独立可读 SystemVerilog，便于检查 Chisel 的位宽与寄存器展开。 */
object EmitVDot16 extends App {
  ChiselStage.emitSystemVerilogFile(new VDot16, args)
}
