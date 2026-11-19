    //////////////////////////////////////////////////////////////////////////////////
    // cp_fp_rnd
    //////////////////////////////////////////////////////////////////////////////////

    cp_fp_rnd : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm")  iff (ins.trap == 0 )  {
        // FCSR.frm for a multiply-accumulate whose partial sum is not exact in the C format (disclosed rnd = frm)
        bins frm_rne = {3'b000};
        bins frm_rtz = {3'b001};
        bins frm_rdn = {3'b010};
        bins frm_rup = {3'b011};
        bins frm_rmm = {3'b100};
    }

    //// end cp_fp_rnd////////////////////////////////////////////////
