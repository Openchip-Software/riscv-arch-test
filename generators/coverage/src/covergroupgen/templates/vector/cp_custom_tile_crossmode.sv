    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_tile_crossmode
    //////////////////////////////////////////////////////////////////////////////////

    cp_tile_crossmode_lambda : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "lambda")  iff (ins.trap == 0 )  {
        // VTYPE.lambda of a transposing tile instruction paired with an order-preserving one
        bins one       = {1};
        bins two       = {2};
        bins four      = {3};
        bins eight     = {4};
        bins sixteen   = {5};
        bins thirtytwo = {6};
        bins sixtyfour = {7};
    }

    cp_tile_crossmode_lmul : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 )  {
        // VTYPE.vlmul of the pair
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_tile_crossmode_ld : coverpoint ins.get_gpr_reg(ins.current.rs2) == x0  iff (ins.trap == 0 )  {
        // Natural LD (rs2 = x0) or a padded LD in a register
        bins natural = {1};
        bins padded  = {0};
    }

    cp_custom_tile_crossmode : cross cp_tile_crossmode_lambda, cp_tile_crossmode_lmul, cp_tile_crossmode_ld  iff (ins.trap == 0 )  {
        // Transposing tile load or store paired with the other mode, for each lambda, LMUL and LD
    }

    //// end cp_custom_tile_crossmode////////////////////////////////////////////////
