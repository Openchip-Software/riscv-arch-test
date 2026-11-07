    //////////////////////////////////////////////////////////////////////////////////
    // cp_altfmt
    //////////////////////////////////////////////////////////////////////////////////

    cp_vtype_altfmt_a : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_a")  iff (ins.trap == 0 )  {
        // VTYPE.altfmt_A; for integer multiply-accumulate, 1 makes A unsigned
        bins signed_a   = {0};
        bins unsigned_a = {1};
    }

    cp_vtype_altfmt_b : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_b")  iff (ins.trap == 0 )  {
        // VTYPE.altfmt_B; for integer multiply-accumulate, 1 makes B unsigned
        bins signed_b   = {0};
        bins unsigned_b = {1};
    }

    cp_altfmt : cross cp_vtype_altfmt_a, cp_vtype_altfmt_b  iff (ins.trap == 0 )  {
        // All four signedness combinations of A and B
    }

    //// end cp_altfmt////////////////////////////////////////////////
