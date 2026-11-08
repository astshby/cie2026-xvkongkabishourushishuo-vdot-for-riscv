# 打开同目录执行波形.vcd.gz，并用本脚本选取实测信号。
set requested [list {selected.TOP__clock} {selected.TOP__SimTop__difftest_timer} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_in_valid} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_in_ready} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_in_bits_ctrl_fuOpType} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_in_bits_data_src_0} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_in_bits_data_src_1} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__dot16__io_enableS1} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__dot16__io_enableS2} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__dot16__pairSumsReg_4} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__dot16__pairSumsReg_5} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_out_valid} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_out_ready} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus_1__Vipu__io_out_bits_res_data} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus__Vimac__io_in_valid} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus__Vimac__io_out_valid} {selected.TOP__SimTop__l_soc__core_with_l2__core__backend__inner_vfExuBlock__exus__Vimac__io_out_bits_res_data}]
set found [list]
set count [gtkwave::getNumFacs]
foreach requested_name $requested {
  for {set i 0} {$i < $count} {incr i} {
    set name [gtkwave::getFacName $i]
    set base [regsub {\[[^]]+\]$} $name ""]
    if {$base eq $requested_name} {lappend found $name; break}
  }
}
if {[llength $found] != [llength $requested]} {error "selected waveform signal missing"}
gtkwave::addSignalsFromList $found
if {[info exists ::env(KKS_WAVE_VIEW)] && $::env(KKS_WAVE_VIEW) eq "baseline"} {
  gtkwave::setZoomRangeTimes 4629 4661
  gtkwave::setMarker 4633
} else {
  gtkwave::setZoomRangeTimes 5013 5025
  gtkwave::setMarker 5017
}
gtkwave::setNamedMarker A 5017 "dot-in"
gtkwave::setNamedMarker B 5019 "dot-out"
gtkwave::setNamedMarker C 4633 "baseline-in"
gtkwave::setNamedMarker D 4657 "baseline-out"
puts "GTKWave stage3 selected [llength $found] signals"
if {[info exists ::env(KKS_WAVE_SMOKE_TEST)]} {exit 0}
