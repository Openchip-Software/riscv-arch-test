    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs2_edges_f_ofp8_sew32
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs2_edges_f_ofp8_e4m3_sew32 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[7:0]  iff (ins.trap == 0 && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_b") == 0)  {
        // (OFP8 E4M3, vtype.altfmt_B = 0)
        bins pos0                     = {8'h00};
        bins neg0                     = {8'h80};
        bins pos1                     = {8'h38};
        bins neg1                     = {8'hB8};
        bins posminnorm               = {8'h08};
        bins posmaxnorm               = {8'h7E};
        bins negmaxnorm               = {8'hFE};
        bins pos0p5                   = {8'h30};
        bins pos1p5                   = {8'h3C};
        bins neg2                     = {8'hC0};
        bins twoToEmax                = {8'h78};
        bins onePulp                  = {8'h39};
        bins largestsubnorm           = {8'h07};
        bins negSubnormLeadingOne     = {8'h84};
        bins min_subnorm              = {8'h01};
        bins posNaN                   = {8'h7F};
        bins negNaN                   = {8'hFF};
    }

    cp_vs2_edges_f_ofp8_e5m2_sew32 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[7:0]  iff (ins.trap == 0 && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "altfmt_b") == 1)  {
        // (OFP8 E5M2, vtype.altfmt_B = 1)
        bins pos0                     = {8'h00};
        bins neg0                     = {8'h80};
        bins pos1                     = {8'h3C};
        bins neg1                     = {8'hBC};
        bins posminnorm               = {8'h04};
        bins posmaxnorm               = {8'h7B};
        bins negmaxnorm               = {8'hFB};
        bins posinfinity              = {8'h7C};
        bins neginfinity              = {8'hFC};
        bins pos0p5                   = {8'h38};
        bins pos1p5                   = {8'h3E};
        bins neg2                     = {8'hC0};
        bins twoToEmax                = {8'h78};
        bins onePulp                  = {8'h3D};
        bins largestsubnorm           = {8'h03};
        bins negSubnormLeadingOne     = {8'h82};
        bins min_subnorm              = {8'h01};
        bins canonicalQNaN            = {8'h7E};
        bins negNoncanonicalQNaN      = {8'hFF};
        bins sNaN_payload1            = {8'h7D};
    }

    //// end cp_vs2_edges_f_ofp8_sew32////////////////////////////////////////////////
