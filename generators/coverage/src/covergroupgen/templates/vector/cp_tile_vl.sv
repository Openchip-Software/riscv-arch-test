    //////////////////////////////////////////////////////////////////////////////////
    // cp_tile_vl
    //////////////////////////////////////////////////////////////////////////////////

    cp_tile_vl : coverpoint vl_check(ins.hart, ins.issue, ime_column_vl(ins.hart, ins.issue))  iff (ins.trap == 0 )  {
        // VL in units of one C column (lambda*LMUL elements)
        bins one_column = {vl_one   };
        bins vlmax      = {vl_vlmax };
        bins legal      = {vl_legal };
    }

    //// end cp_tile_vl////////////////////////////////////////////////
