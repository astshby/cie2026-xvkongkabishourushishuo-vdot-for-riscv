package xiangshan

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import xiangshan.backend.decode.KksVDot
import xiangshan.backend.fu.vector.VDot16

/** 使用真正的指令匹配定义和配置函数，检查保留编码与非法配置。 */
class VDotConfigProbe extends Module {
  val io = IO(new Bundle {
    val vill = Input(Bool())
    val sew = Input(UInt(3.W))
    val lmul = Input(UInt(3.W))
    val vl = Input(UInt(9.W))
    val vstart = Input(UInt(9.W))
    val vm = Input(Bool())
    val illegal = Output(Bool())
  })
  io.illegal := KksVDot.unsupported(io.vill, io.sew, io.lmul, io.vl, io.vstart, io.vm)
}

class VDot16Spec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "VDot16"

  it should "match only the experimental OPIVV encoding for every register field" in {
    val p = KksVDot.instruction
    assert(p.value == KksVDot.DecodeMatch && p.mask == KksVDot.DecodeMask)
    def matches(inst: BigInt): Boolean = (inst & p.mask) == p.value
    for (vd <- 0 until 32; vs2 <- 0 until 32; vs1 <- 0 until 32; vm <- 0 to 1) {
      val word = BigInt(0x57) | BigInt(vd << 7) | BigInt(vs1 << 15) |
        BigInt(vs2 << 20) | BigInt(vm << 25) | (BigInt(3) << 26)
      assert(matches(word))
    }
    for (funct6 <- 0 until 64; funct3 <- 0 until 8) {
      val word = (BigInt(funct6) << 26) | BigInt(1 << 25) | BigInt(funct3 << 12) | 0x57
      assert(matches(word) == (funct6 == 3 && funct3 == 0))
    }
    assert(!matches(KksVDot.UnmaskedMatch ^ 1)) // opcode变化不得匹配。
    println("VDOT_ENCODING PASS register_encodings=65536 opcode_classes=512")
  }

  it should "reject each unsupported vector configuration" in {
    case class C(vill: Boolean=false, sew: Int=0, lmul: Int=0, vl: Int=16,
                 start: Int=0, vm: Boolean=true)
    val good = C()
    val cases = Seq(good) ++ (1 to 7).map(x => good.copy(sew=x)) ++
      (1 to 7).map(x => good.copy(lmul=x)) ++
      ((0 to 15) ++ Seq(17,31,255)).map(x => good.copy(vl=x)) ++
      Seq(1,2,15,16,127).map(x => good.copy(start=x)) ++
      Seq(good.copy(vill=true), good.copy(vm=false))
    test(new VDotConfigProbe).withAnnotations(Seq(TreadleBackendAnnotation)) { dut =>
      cases.foreach { c =>
        dut.io.vill.poke(c.vill.B); dut.io.sew.poke(c.sew.U); dut.io.lmul.poke(c.lmul.U)
        dut.io.vl.poke(c.vl.U); dut.io.vstart.poke(c.start.U); dut.io.vm.poke(c.vm.B)
        dut.io.illegal.expect((c != good).B)
      }
    }
    println(s"VDOT_CONFIG PASS cases=${cases.size}")
  }

  private def pack(xs: Seq[Int]): BigInt = xs.zipWithIndex.foldLeft(BigInt(0)) {
    case (bits, (x,i)) => bits | (BigInt(x & 255) << (8*i))
  }
  private def golden(a: Seq[Int], b: Seq[Int]): BigInt =
    a.zip(b).map { case (x,y) => BigInt(x)*BigInt(y) }.sum & ((BigInt(1)<<32)-1)

  // 只建立事务结果的两级时间模型，参考运算是标量BigInt点积，不复用RTL加法树。
  private class Driver(dut: VDot16) {
    private var first: Option[BigInt] = None
    private var output: Option[BigInt] = None
    private var cycle = 0
    def tick(a: Seq[Int], b: Seq[Int], en1: Boolean=true, en2: Boolean=true): Unit = {
      dut.io.vs1.poke(pack(a).U); dut.io.vs2.poke(pack(b).U)
      dut.io.enableS1.poke(en1.B); dut.io.enableS2.poke(en2.B)
      if (en2) output = first
      if (en1) first = Some(golden(a,b))
      dut.clock.step(); cycle += 1
      output.foreach(x => dut.io.result.expect(x.U, s"cycle=$cycle en1=$en1 en2=$en2"))
    }
  }

  it should "exhaust all 65536 signed byte products through the full sixteen-lane sum" in {
    test(new VDot16).withAnnotations(Seq(TreadleBackendAnnotation)) { dut =>
      dut.clock.setTimeout(0)
      val driver = new Driver(dut)
      for (a <- -128 to 127; b <- -128 to 127) driver.tick(Seq.fill(16)(a),Seq.fill(16)(b))
      driver.tick(Seq.fill(16)(0),Seq.fill(16)(0))
      driver.tick(Seq.fill(16)(0),Seq.fill(16)(0))
    }
    println("VDOT_EXHAUSTIVE PASS signed_byte_pairs=65536 full128=checked")
  }

  it should "keep all lanes, independent stage holds and back-to-back signed results" in {
    test(new VDot16).withAnnotations(Seq(TreadleBackendAnnotation)) { dut =>
      dut.clock.setTimeout(0)
      val driver = new Driver(dut)
      for (lane <- 0 until 16; (a,b) <- Seq((-128,-128),(-128,127),(127,-128),(127,127))) {
        driver.tick(Seq.tabulate(16)(i => if(i==lane) a else 0),
                    Seq.tabulate(16)(i => if(i==lane) b else 0))
      }
      val rng = new scala.util.Random(0x56444f54L)
      for (cycle <- 0 until 2048) {
        val a=Seq.fill(16)(rng.nextInt(256)-128)
        val b=Seq.fill(16)(rng.nextInt(256)-128)
        // 四种使能组合轮换，再加入随机气泡，覆盖一拍只更新其中一级。
        driver.tick(a,b, (cycle & 1)==0 || rng.nextBoolean(), (cycle & 2)==0 || rng.nextBoolean())
      }
      driver.tick(Seq.fill(16)(0),Seq.fill(16)(0),false,true)
      driver.tick(Seq.fill(16)(0),Seq.fill(16)(0),false,false)
    }
    println("VDOT_PIPELINE PASS one_hot_cases=64 enable_cycles=2048 full128=checked")
  }
}
