    //////////////////////////////////////////////////////////////////////////////////
    // cr_tile_vtype_agnostic
    //////////////////////////////////////////////////////////////////////////////////

    cp_vtype_vta_tile : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vta")  iff (ins.trap == 0 )  {
        // VTYPE.vta; a tile load leaves tail elements undisturbed for either value
        bins undisturbed = {0};
        bins agnostic    = {1};
    }

    cp_vtype_vma_tile : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vma")  iff (ins.trap == 0 )  {
        // VTYPE.vma; a tile load leaves inactive elements undisturbed for either value
        bins undisturbed = {0};
        bins agnostic    = {1};
    }

    cr_tile_vtype_agnostic : cross cp_vtype_vta_tile, cp_vtype_vma_tile  iff (ins.trap == 0 )  {
        // All four combinations of vta and vma on a tile load
    }

    //// end cr_tile_vtype_agnostic////////////////////////////////////////////////
