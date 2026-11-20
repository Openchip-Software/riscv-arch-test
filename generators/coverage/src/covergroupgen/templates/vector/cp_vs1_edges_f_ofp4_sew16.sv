    //////////////////////////////////////////////////////////////////////////////////
    // cp_vs1_edges_f_ofp4_sew16
    //////////////////////////////////////////////////////////////////////////////////

    cp_vs1_edges_f_ofp4_sew16 : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs1_val)[3:0]  iff (ins.trap == 0 )  {
        // (OFP4 E2M1, every encoding)
        bins pos0                     = {4'h0};
        bins pos0p5                   = {4'h1};
        bins pos1                     = {4'h2};
        bins pos1p5                   = {4'h3};
        bins pos2                     = {4'h4};
        bins pos3                     = {4'h5};
        bins pos4                     = {4'h6};
        bins pos6                     = {4'h7};
        bins neg0                     = {4'h8};
        bins neg0p5                   = {4'h9};
        bins neg1                     = {4'hA};
        bins neg1p5                   = {4'hB};
        bins neg2                     = {4'hC};
        bins neg3                     = {4'hD};
        bins neg4                     = {4'hE};
        bins neg6                     = {4'hF};
    }

    //// end cp_vs1_edges_f_ofp4_sew16////////////////////////////////////////////////
