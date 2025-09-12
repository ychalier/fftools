import pathlib

import tqdm

from ..tool import OneToOneTool
from .. import utils


class Carve(OneToOneTool):
    """
    @see https://en.m.wikipedia.org/wiki/Seam_carving
    @see https://github.com/andrewdcampbell/seam-carving
    @see https://github.com/andrewdcampbell/seam-carving/pull/4/files
    """

    NAME = "carve"
    DESC = "Resize an image with seam carving."
    OUTPUT_PATH_TEMPLATE = "{parent}/{stem}_carved_{width}x{height}{suffix}"

    def __init__(self,
            template: str,
            width: int,
            height: int):
        OneToOneTool.__init__(self, template)
        self.width = width
        self.height = height

    @staticmethod
    def add_arguments(parser):
        OneToOneTool.add_arguments(parser)
        parser.add_argument("width", type=int, default=None, help="target width in pixels")
        parser.add_argument("height", type=int, default=None, help="target height in pixels")

    def process(self, input_path: pathlib.Path) -> pathlib.Path:
        probe_result = utils.ffprobe(input_path)
        dx = self.width - probe_result.width
        dy = self.height - probe_result.height
        output_path = self.inflate(input_path, {
            "width": self.width,
            "height": self.height,
        })
        seam_carve(input_path, dx, dy, output_path)
        return output_path


def seam_carve(
        input_path: pathlib.Path,
        dx: int,
        dy: int,
        output_path: pathlib.Path,
        use_forward_energy: bool = True
        ):
    import cv2, numba, numpy, scipy.ndimage

    def rotate_image(image, clockwise):
        k = 1 if clockwise else 3
        return numpy.rot90(image, k)

    def backward_energy(im):
        xgrad = scipy.ndimage.convolve1d(im, numpy.array([1, 0, -1]), axis=1, mode='wrap')
        ygrad = scipy.ndimage.convolve1d(im, numpy.array([1, 0, -1]), axis=0, mode='wrap')
        grad_mag = numpy.sqrt(numpy.sum(xgrad**2, axis=2) + numpy.sum(ygrad**2, axis=2))
        return grad_mag
    
    def forward_energy(im):
        """
        Forward energy algorithm as described in "Improved Seam Carving for Video Retargeting"
        by Rubinstein, Shamir, Avidan.

        Vectorized code adapted from
        https://github.com/axu2/improved-seam-carving.
        """
        h, w = im.shape[:2]
        im = cv2.cvtColor(im.astype(numpy.uint8), cv2.COLOR_BGR2GRAY).astype(numpy.float64)
        
        energy = numpy.zeros((h, w))
        m = numpy.zeros((h, w))

        U = numpy.roll(im, 1, axis=0)
        L = numpy.roll(im, 1, axis=1)
        R = numpy.roll(im, -1, axis=1)

        cU = numpy.abs(R - L)
        cL = numpy.abs(U - L) + cU
        cR = numpy.abs(U - R) + cU

        for i in range(1, h):
            mU = m[i-1]
            mL = numpy.roll(mU, 1)
            mR = numpy.roll(mU, -1)

            mULR = numpy.array([mU, mL, mR])
            cULR = numpy.array([cU[i], cL[i], cR[i]])
            mULR += cULR

            argmins = numpy.argmin(mULR, axis=0)
            m[i] = numpy.choose(argmins, mULR)
            energy[i] = numpy.choose(argmins, cULR)

        return energy

    @numba.njit
    def add_seam(im, seam_idx):
        """
        Add a vertical seam to a 3-channel color image at the indices provided
        by averaging the pixels values to the left and right of the seam.

        Code adapted from https://github.com/vivianhylee/seam-carving.
        """
        h, w = im.shape[:2]
        output = numpy.zeros((h, w + 1, 3))
        for row in range(h):
            col = seam_idx[row]
            for ch in range(3):
                if col == 0:
                    p = numpy.mean(im[row, col: col + 2, ch])
                    output[row, col, ch] = im[row, col, ch]
                    output[row, col + 1, ch] = p
                    output[row, col + 1:, ch] = im[row, col:, ch]
                else:
                    p = numpy.mean(im[row, col - 1: col + 1, ch])
                    output[row, : col, ch] = im[row, : col, ch]
                    output[row, col, ch] = p
                    output[row, col + 1:, ch] = im[row, col:, ch]

        return output

    def remove_seam(im, boolmask):
        h, w = im.shape[:2]
        boolmask3c = numpy.stack([boolmask] * 3, axis=2)
        return im[boolmask3c].reshape((h, w - 1, 3))

    def get_minimum_seam(im):
        """
        DP algorithm for finding the seam of minimum energy. Code adapted from
        https://karthikkaranth.me/blog/implementing-seam-carving-with-python/
        """
        h, w = im.shape[:2]
        energyfn = forward_energy if use_forward_energy else backward_energy
        M = energyfn(im)
        seam_idx, boolmask = compute_shortest_path(M, im, h, w)
        return numpy.array(seam_idx), boolmask

    @numba.njit
    def compute_shortest_path(M, im, h, w):
        backtrack = numpy.zeros_like(M, dtype=numpy.int_)
        for i in range(1, h):
            for j in range(0, w):
                if j == 0:
                    idx = numpy.argmin(M[i - 1, j:j + 2])
                    backtrack[i, j] = idx + j
                    min_energy = M[i-1, idx + j]
                else:
                    idx = numpy.argmin(M[i - 1, j - 1:j + 2])
                    backtrack[i, j] = idx + j - 1
                    min_energy = M[i - 1, idx + j - 1]

                M[i, j] += min_energy

        seam_idx = []
        boolmask = numpy.ones((h, w), dtype=numpy.bool_)
        j = numpy.argmin(M[-1])
        for i in range(h-1, -1, -1):
            boolmask[i, j] = False
            seam_idx.append(j)
            j = backtrack[i, j]

        seam_idx.reverse()
        return seam_idx, boolmask

    def seams_removal(im, num_remove, pbar: tqdm.tqdm):
        pbar.set_description("Seams removal")
        for _ in range(num_remove):
            seam_idx, boolmask = get_minimum_seam(im)
            im = remove_seam(im, boolmask)
            pbar.update(1)
        return im

    def seams_insertion(im, num_add, pbar: tqdm.tqdm):
        pbar.set_description("Seams insertion")
        seams_record = []
        temp_im = im.copy()
        for _ in range(num_add):
            seam_idx, boolmask = get_minimum_seam(temp_im)
            seams_record.append(seam_idx)
            temp_im = remove_seam(temp_im, boolmask)
            pbar.update(1)
        seams_record.reverse()
        for _ in range(num_add):
            seam = seams_record.pop()
            im = add_seam(im, seam)
            for remaining_seam in seams_record:
                remaining_seam[numpy.where(remaining_seam >= seam)] += 2
            pbar.update(1)
        return im

    im = cv2.imread(input_path.as_posix()).astype(numpy.float64)
    h, w = im.shape[:2]
    assert h + dy > 0 and w + dx > 0 and dy <= h and dx <= w
    output = im
    total = 0
    if dx < 0:
        total += abs(dx)
    else:
        total += 2 * dx
    if dy < 0:
        total += abs(dy)
    else:
        total += 2 * dy 
    pbar = tqdm.tqdm(total=total)
    if dx < 0:
        output = seams_removal(output, -dx, pbar)
    elif dx > 0:
        output = seams_insertion(output, dx, pbar)
    if dy < 0:
        output = rotate_image(output, True)
        output = seams_removal(output, -dy, pbar)
        output = rotate_image(output, False)
    elif dy > 0:
        output = rotate_image(output, True)
        output = seams_insertion(output, dy, pbar)
        output = rotate_image(output, False)
    pbar.close()
    cv2.imwrite(output_path.as_posix(), output.astype(numpy.uint8))
