    //////////////////////////////////////////////////////////////////////////////////
    // cp_ld
    //////////////////////////////////////////////////////////////////////////////////

    cp_ld : coverpoint ime_ld_check(ins.hart, ins.issue, ins.get_gpr_reg(ins.current.rs2) == x0, ins.current.rs2_val, ins.current.insn[31:29])  iff (ins.trap == 0 )  {
        // Leading dimension LD of a tile load or store, against linesize = lambda*LMUL
        bins x0     = {ime_ld_x0    };   // rs2 = x0: natural LD
        bins zero   = {ime_ld_zero  };   // rs2 holds 0: natural LD
        bins tight  = {ime_ld_tight };   // LD = linesize
        bins padded = {ime_ld_padded};   // LD = linesize + 1
        bins double = {ime_ld_double};   // LD = 2*linesize
    }

    //// end cp_ld////////////////////////////////////////////////
