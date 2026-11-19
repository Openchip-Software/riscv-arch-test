    //////////////////////////////////////////////////////////////////////////////////
    // cp_ime_vd_overlap
    //////////////////////////////////////////////////////////////////////////////////

    cp_ime_vd_overlap : coverpoint ime_vd_overlap(ins.hart, ins.issue, ins.current.insn[11:7], ins.current.insn[19:15], ins.current.insn[24:20]) {
        // The C group (vd) overlaps the A group (vs1) or the B group (vs2), including at VL = 0
        bins vs1_base = {ime_overlap_vs1_base};
        bins vs2_base = {ime_overlap_vs2_base};
        bins vs2_inside = {ime_overlap_vs2_inside};
        bins vs1_base_vl0 = {ime_overlap_vs1_base_vl0};
    }

    //// end cp_ime_vd_overlap////////////////////////////////////////////////
