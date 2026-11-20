    //////////////////////////////////////////////////////////////////////////////////
    // cp_ime_mx_v0_overlap
    //////////////////////////////////////////////////////////////////////////////////

    cp_ime_mx_v0_overlap : coverpoint {ins.current.insn[11:7] == 0, ins.current.insn[19:15] == 0, ins.current.insn[24:20] == 0}  iff (ins.current.insn[25] == 0)  {
        // Microscaled: the vd, vs1 or vs2 group starts at v0, which holds the block scales
        bins vd_v0 = {3'b100};
        bins vs1_v0 = {3'b010};
        bins vs2_v0 = {3'b001};
    }

    //// end cp_ime_mx_v0_overlap////////////////////////////////////////////////
