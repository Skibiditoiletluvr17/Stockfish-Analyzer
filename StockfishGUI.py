import tkinter as tk
from tkinter import messagebox
import chess
import chess.engine
import sys
import os
import shutil
import threading
import time

STOCKFISH_PATH = None

def find_stockfish():
    # If running as a PyInstaller bundle, look in the unpacked folder
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        bundled_sf = os.path.join(bundle_dir, "stockfish.exe")
        if os.path.exists(bundled_sf):
            return bundled_sf

    # Otherwise, look in same folder as script/EXE
    here = os.path.dirname(os.path.abspath(sys.argv[0]))
    local_sf = os.path.join(here, "stockfish.exe")
    if os.path.exists(local_sf):
        return local_sf

    messagebox.showerror("Stockfish Not Found",
                         "Stockfish was not found.\n"
                         "Please make sure 'stockfish.exe' is in the same folder as this program.")
    sys.exit(1)

class ChessGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Stockfish Analyzer - v2.17")
        self.board = chess.Board()
        self.engine = None
        self.analysis_thread = None
        self.running = False
        self.selected_square = None

        self.create_widgets()
        self.start_engine()
        self.update_board()
        self.start_analysis()

    def create_widgets(self):
        self.left_frame = tk.Frame(self.root, bg="gray")
        self.left_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        self.squares = {}
        colors = ["#f0d9b5", "#b58863"]

        for r in range(8):
            for c in range(8):
                color = colors[(r + c) % 2]
                lbl = tk.Label(
                    self.left_frame,
                    text=" ",  # space prevents collapse
                    width=2,
                    height=1,
                    font=("Segoe UI Emoji", 32),
                    bg=color,
                    anchor="center"
                )
                lbl.grid(row=r, column=c, sticky="nsew")
                lbl.bind("<Button-1>", lambda e, row=r, col=c: self.square_clicked(row, col))
                self.squares[(r, c)] = lbl

        # Force grid squares to always be equal size
        for r in range(8):
            self.left_frame.rowconfigure(r, weight=1, uniform="board")
        for c in range(8):
            self.left_frame.columnconfigure(c, weight=1, uniform="board")

        # Right side (engine analysis)
        self.right_frame = tk.Frame(self.root, bg="black")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH)

        self.eval_label = tk.Label(self.right_frame, text="Engine Analysis", fg="white", bg="black", font=("Segoe UI", 12, "bold"))
        self.eval_label.pack(pady=5)

        self.eval_text = tk.Text(self.right_frame, width=30, height=20, bg="black", fg="white")
        self.eval_text.pack(padx=5, pady=5)

        self.button_frame = tk.Frame(self.right_frame, bg="black")
        self.button_frame.pack(pady=5)

        tk.Button(self.button_frame, text="Play", command=self.play_move).grid(row=0, column=0, padx=2)
        tk.Button(self.button_frame, text="Undo", command=self.undo_move).grid(row=0, column=1, padx=2)
        tk.Button(self.button_frame, text="Quit", command=self.quit_game).grid(row=0, column=2, padx=2)

    def start_engine(self):
        global STOCKFISH_PATH
        STOCKFISH_PATH = find_stockfish()
        try:
            self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
        except Exception as e:
            messagebox.showerror("Engine Error", f"Could not start Stockfish:\n{e}")
            sys.exit(1)

    def start_analysis(self):
        self.running = True
        self.analysis_thread = threading.Thread(target=self.analyze, daemon=True)
        self.analysis_thread.start()

    def analyze(self):
        while self.running:
            try:
                # Ask Stockfish for MULTIPV=3 (top 3 lines)
                result = self.engine.analyse(
                    self.board,
                    chess.engine.Limit(depth=12),
                    multipv=3
                )

                # Build pretty text output 
                lines = []
                for idx, info in enumerate(result, start=1):
                    score = info["score"].white()
                    if score.is_mate():
                        eval_str = f"Mate in {score.mate()}"
                    else:
                        eval_str = f"{score.score() / 100:.2f}"

                    move_line = " ".join([m.uci() for m in info.get("pv", [])])
                    lines.append(f"PV{idx}: {eval_str} | {move_line}")

                # Update text box
                time.sleep(2)
                self.eval_text.delete("1.0", tk.END)
                self.eval_text.insert(tk.END, "\n".join(lines))

            except Exception:
                pass

    def square_to_uci(self, r, c):
        file = chr(ord("a") + c)
        rank = str(8 - r)
        return file + rank

    def square_clicked(self, r, c):
        square = self.square_to_uci(r, c)
        if self.selected_square:
            move = chess.Move.from_uci(self.selected_square + square)
            if move in self.board.legal_moves:
                self.board.push(move)
            self.selected_square = None
        else:
            if self.board.piece_at(chess.parse_square(square)):
                self.selected_square = square
        self.update_board()

    def update_board(self):
        board_fen = self.board.fen().split()[0]
        rows = board_fen.split("/")
        for r in range(8):
            row = rows[r]
            c = 0
            for ch in row:
                if ch.isdigit():
                    for _ in range(int(ch)):
                        self.squares[(r, c)].config(text=" ")
                        c += 1
                else:
                    self.squares[(r, c)].config(text=self.get_piece_symbol(ch))
                    c += 1

    def get_piece_symbol(self, piece_char):
        symbols = {
            "P": "♙", "N": "♘", "B": "♗", "R": "♖", "Q": "♕", "K": "♔",
            "p": "♟", "n": "♞", "b": "♝", "r": "♜", "q": "♛", "k": "♚"
        }
        return symbols.get(piece_char, "?")

    def play_move(self):
        # Placeholder: let engine make a move
        try:
            result = self.engine.play(self.board, chess.engine.Limit(depth=15))
            self.board.push(result.move)
            self.update_board()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def undo_move(self):
        if len(self.board.move_stack) > 0:
            self.board.pop()
            self.update_board()

    def quit_game(self):
        self.running = False
        if self.engine:
            self.engine.quit()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    gui = ChessGUI(root)
    root.mainloop()
