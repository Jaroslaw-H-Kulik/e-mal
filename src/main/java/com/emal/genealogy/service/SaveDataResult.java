package com.emal.genealogy.service;

/** Mirrors save_genealogy_data's fixed response shape (server.py) - always {'status': 'success', 'message': ...}, never a failure variant. */
public record SaveDataResult(String status, String message) {

    public SaveDataResult() {
        this("success", "Data saved successfully");
    }
}
