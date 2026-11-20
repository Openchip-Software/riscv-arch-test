    //////////////////////////////////////////////////////////////////////////////////
    // cp_altfmt_ofp8
    //////////////////////////////////////////////////////////////////////////////////

    cp_vtype_altfmt_a_ofp8 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_a")  iff (ins.trap == 0 )  {
        // VTYPE.altfmt_A; for OFP8 inputs, 1 selects E5M2 for A
        bins e4m3_a = {0};
        bins e5m2_a = {1};
    }

    cp_vtype_altfmt_b_ofp8 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_b")  iff (ins.trap == 0 )  {
        // VTYPE.altfmt_B; for OFP8 inputs, 1 selects E5M2 for B
        bins e4m3_b = {0};
        bins e5m2_b = {1};
    }

    cp_altfmt_ofp8 : cross cp_vtype_altfmt_a_ofp8, cp_vtype_altfmt_b_ofp8  iff (ins.trap == 0 )  {
        // All four OFP8 format combinations of A and B
    }

    //// end cp_altfmt_ofp8////////////////////////////////////////////////
