    //////////////////////////////////////////////////////////////////////////////////
    // cp_ime_mx_bs16_lmul_e16
    //////////////////////////////////////////////////////////////////////////////////

    cp_ime_mx_bs16_lmul_e16 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")  iff (ins.current.insn[25] == 0 && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "bs") == 1 && get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") == 1)  {
        // Microscaled with vtype.bs = 1 at SEW = 16 and LMUL = 8: W*LMUL = 32 > SEW
        bins m8 = {3};
    }

    //// end cp_ime_mx_bs16_lmul_e16////////////////////////////////////////////////
