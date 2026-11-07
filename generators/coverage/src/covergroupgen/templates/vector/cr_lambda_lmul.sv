    //////////////////////////////////////////////////////////////////////////////////
    // cr_lambda_lmul
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vtype_lambda : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "lambda")  iff (ins.trap == 0 )  {
        // Value of VTYPE.lambda, encoded as log2(lambda) + 1
        bins one       = {1};
        bins two       = {2};
        bins four      = {3};
        bins eight     = {4};
        bins sixteen   = {5};
        bins thirtytwo = {6};
        bins sixtyfour = {7};
    }

    cp_csr_vtype_lmul_ime : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.trap == 0 )  {
        // Value of VTYPE.vlmul; IME instructions reserve fractional LMUL
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_csr_vl_vlmax : coverpoint vl_check(ins.hart, ins.issue)  iff (ins.trap == 0 )  {
        // VL = VLMAX
        bins vlmax = {vl_vlmax};
    }

    cr_lambda_lmul : cross cp_csr_vtype_lambda, cp_csr_vtype_lmul_ime, cp_csr_vl_vlmax  iff (ins.trap == 0 )  {
        // Cross coverage of lambda and integer LMUL at VL = VLMAX
    }

    //////////////////////////////////////////////////////////////////////////////////

    //// end cr_lambda_lmul////////////////////////////////////////////////
