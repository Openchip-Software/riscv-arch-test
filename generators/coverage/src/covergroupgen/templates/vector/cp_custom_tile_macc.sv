    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_tile_macc
    //////////////////////////////////////////////////////////////////////////////////

    cp_tile_macc_lambda : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "lambda")  iff (ins.trap == 0 )  {
        // VTYPE.lambda of a multiply-accumulate whose A and B come from tile loads
        bins one       = {1};
        bins two       = {2};
        bins four      = {3};
        bins eight     = {4};
        bins sixteen   = {5};
        bins thirtytwo = {6};
        bins sixtyfour = {7};
    }

    cp_tile_macc_lmul : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 )  {
        // VTYPE.vlmul of the multiply-accumulate (the tile LMUL of A and B)
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_tile_macc : cross cp_tile_macc_lambda, cp_tile_macc_lmul  iff (ins.trap == 0 )  {
        // Multiply-accumulate with tile-loaded A and B and a tile-stored C, for each lambda and LMUL
    }

    //// end cp_custom_tile_macc////////////////////////////////////////////////
