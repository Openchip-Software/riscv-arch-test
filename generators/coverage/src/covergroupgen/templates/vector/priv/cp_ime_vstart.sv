    //////////////////////////////////////////////////////////////////////////////////
    // cp_ime_vstart
    //////////////////////////////////////////////////////////////////////////////////

    cp_ime_vstart : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        // vstart before an IME instruction: reserved for multiply-accumulate, a resume point for tile loads and stores
        bins one = {1};
        bins above_one = {[2:$]};
    }

    //// end cp_ime_vstart////////////////////////////////////////////////
