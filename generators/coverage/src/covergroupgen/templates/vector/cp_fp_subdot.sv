    //////////////////////////////////////////////////////////////////////////////////
    // cp_fp_subdot
    //////////////////////////////////////////////////////////////////////////////////

    cp_fp_subdot : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "frm")  iff (ins.trap == 0 )  {
        // FCSR.frm for a widening multiply-accumulate whose W products add up to one ULP of C
        bins ulp_rne = {3'b000};
        bins ulp_rtz = {3'b001};
        bins ulp_rdn = {3'b010};
        bins ulp_rup = {3'b011};
        bins ulp_rmm = {3'b100};
    }

    //// end cp_fp_subdot////////////////////////////////////////////////
