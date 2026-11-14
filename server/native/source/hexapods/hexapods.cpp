#include "stream_hexapod.hpp"
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc == 2 && std::string(argv[1]) == "--stream-hexapod-preview") return Hexapods::streamHexapod(true);
    if (argc == 1 || (argc == 2 && std::string(argv[1]) == "--stream-hexapod")) return Hexapods::streamHexapod();
    std::cerr << "Usage: hexapods [--stream-hexapod | --stream-hexapod-preview]\n";
    return 1;
}
