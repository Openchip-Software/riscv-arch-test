    //////////////////////////////////////////////////////////////////////////////////
    // cp_scale_fp32
    //////////////////////////////////////////////////////////////////////////////////

    cp_scale_pair_fp32 : coverpoint ins.current.v0_val[15:0]  iff (ins.trap == 0 & ins.current.insn[25] == 1'b0)  {
        // Paired E8M0 scales of element 0 of v0: scale_A of row 0 in bits 7:0, scale_B of column 0 in bits 15:8
        wildcard bins nan_a = {16'b????????11111111};
        wildcard bins nan_b = {16'b11111111????????};
        bins min_max = {16'hFE00};  // scale_A = 2^-127, scale_B = 2^127
        bins max_min = {16'h00FE};  // scale_A = 2^127, scale_B = 2^-127
    }

    cp_scale_combined_fp32 : coverpoint int'(ins.current.v0_val[7:0]) + int'(ins.current.v0_val[15:8]) - 254  iff (ins.trap == 0 & ins.current.insn[25] == 1'b0 & ins.current.v0_val[7:0] != 8'hFF & ins.current.v0_val[15:8] != 8'hFF)  {
        // Combined exponent of the scales of element 0 of v0, outside the exponent range of an FP32 C
        bins underflow = {[-254:-150]};  // below the smallest fp32 subnormal, 2^-149
        bins overflow  = {[128:254]};  // above the largest fp32 exponent, 127
    }

    //// end cp_scale_fp32////////////////////////////////////////////////
