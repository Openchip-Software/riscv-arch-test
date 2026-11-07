    //////////////////////////////////////////////////////////////////////////////////
    // cp_imm_lambda
    //////////////////////////////////////////////////////////////////////////////////

    cp_imm_lambda : coverpoint ins.current.insn[31:29]  iff (ins.trap == 0 )  {
        // Immediate lambda of a tile load or store; 0 uses vtype.lambda
        bins none = {3'b000};
        bins L1   = {3'b001};
        bins L2   = {3'b010};
        bins L4   = {3'b011};
        bins L8   = {3'b100};
        bins L16  = {3'b101};
        bins L32  = {3'b110};
        bins L64  = {3'b111};
    }

    //// end cp_imm_lambda////////////////////////////////////////////////
