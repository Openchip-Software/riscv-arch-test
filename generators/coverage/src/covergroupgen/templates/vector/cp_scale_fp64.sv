    //////////////////////////////////////////////////////////////////////////////////
    // cp_scale_fp64
    //////////////////////////////////////////////////////////////////////////////////

    cp_scale_pair_fp64 : coverpoint ins.current.v0_val[15:0]  iff (ins.trap == 0 & ins.current.insn[25] == 1'b0)  {
        // Paired E8M0 scales of element 0 of v0: scale_A of row 0 in bits 7:0, scale_B of column 0 in bits 15:8
        wildcard bins nan_a = {16'b????????11111111};
        wildcard bins nan_b = {16'b11111111????????};
        bins min_max = {16'hFE00};  // scale_A = 2^-127, scale_B = 2^127
        bins max_min = {16'h00FE};  // scale_A = 2^127, scale_B = 2^-127
    }

    //// end cp_scale_fp64////////////////////////////////////////////////
